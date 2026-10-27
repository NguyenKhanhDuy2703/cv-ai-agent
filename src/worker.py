"""Independent durable worker: python -m src.worker."""
import asyncio
import logging
import signal
from datetime import datetime, timezone
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError as DatabaseTimeoutError

from .config import settings
from .jobs.database import Database, configure_event_loop
from .jobs.repository import JobRepository, LeaseLost
from .llm.factory import get_llm_provider
from .llm.operations import JOB_CONTEXT, safe_error_details
from .pipeline.generation import CvGenerationPipeline
from .schemas.canonical_validator import assert_canonical_document
from .schemas.generation import GenerateCvRequest, GenerateCvResult
from .yaml_layer.io import serialize_yaml

logger = logging.getLogger(__name__)


def build_pipeline():
    return CvGenerationPipeline(provider=get_llm_provider())


class GenerationWorker:
    def __init__(self, repository: JobRepository, pipeline_factory=build_pipeline):
        self.repository = repository
        self.config = repository.config
        self.pipeline_factory = pipeline_factory
        self.tasks: set[asyncio.Task] = set()

    async def _generate(self, job):
        async def on_event(event):
            await self.repository.append(job.id, job.lease_token, event)

        request = GenerateCvRequest.model_validate(job.input_snapshot)
        result = GenerateCvResult.model_validate(await self.pipeline_factory().generate(request, on_event=on_event))
        if result.report.request_id != job.request_id or result.report.generation_id != job.generation_id:
            raise ValueError("Pipeline result identifiers do not match the job")
        if result.status in {"success", "partial"}:
            assert_canonical_document(result.document)
            result.cv_yaml = serialize_yaml({"cv": result.document["cv"]})
        elif result.document is not None or result.cv_yaml is not None:
            raise ValueError("Unsuccessful generation cannot contain a CV")
        error = {"code": "GENERATION_FAILED", "message": "Generation failed"} if result.status == "failed" else None
        await self.repository.finish(job.id, job.lease_token, result, error)

    async def _heartbeat(self, job):
        while True:
            await asyncio.sleep(self.config.ai_heartbeat_seconds)
            await self.repository.heartbeat(job.id, job.lease_token)

    async def run_one(self, job):
        context_token = JOB_CONTEXT.set({"jobId": job.id, "requestId": job.request_id, "attempt": str(job.attempt)})
        logger.info("Generation started jobId=%s requestId=%s attempt=%s", job.id, job.request_id, job.attempt)
        generation = asyncio.create_task(self._generate(job))
        heartbeat = asyncio.create_task(self._heartbeat(job))
        try:
            remaining = max(0, (job.deadline_at - datetime.now(timezone.utc)).total_seconds())
            done, _ = await asyncio.wait(
                {generation, heartbeat}, timeout=remaining, return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                return
            if generation in done:
                await generation
            else:
                await heartbeat
        except asyncio.CancelledError:
            raise
        except LeaseLost:
            logger.info("Generation lease lost jobId=%s attempt=%s", job.id, job.attempt)
        except (InterfaceError, OperationalError, DatabaseTimeoutError):
            # A database outage must not turn a recoverable attempt into a terminal
            # pipeline failure. The lease/recovery budget bounds the next attempt.
            logger.warning("Database interruption deferred to lease recovery jobId=%s", job.id)
        except Exception as error:
            details = safe_error_details(error)
            logger.error("Generation failed jobId=%s requestId=%s attempt=%s code=%s stage=%s schema=%s errorType=%s location=%s",
                         job.id, job.request_id, job.attempt, details["code"], details["stage"],
                         details.get("schema", "unknown"), details["errorType"], details.get("location", "unknown"))
            try:
                await self.repository.fail(job.id, job.lease_token, details["code"], details["message"], details=details)
            except Exception:
                logger.warning("Generation finalization deferred to lease recovery jobId=%s", job.id)
        finally:
            generation.cancel()
            heartbeat.cancel()
            await asyncio.gather(generation, heartbeat, return_exceptions=True)
            try:
                await self.repository.release(job.id, job.lease_token)
            except LeaseLost:
                pass
            except Exception:
                logger.warning("Generation lease release deferred jobId=%s", job.id)
            JOB_CONTEXT.reset(context_token)

    async def tick(self):
        await self.repository.maintain()
        while len(self.tasks) < self.config.ai_worker_concurrency:
            job = await self.repository.claim()
            if job is None:
                break
            task = asyncio.create_task(self.run_one(job))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

    async def run(self, stop: asyncio.Event):
        try:
            while not stop.is_set():
                try:
                    await self.tick()
                except Exception as error:
                    logger.warning("Worker polling failed errorType=%s", type(error).__name__)
                try:
                    await asyncio.wait_for(stop.wait(), timeout=self.config.ai_worker_poll_seconds)
                except asyncio.TimeoutError:
                    pass
        finally:
            await self.shutdown()

    async def shutdown(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.tasks.clear()


async def main(pipeline_factory=None):
    if pipeline_factory is None:
        settings.validate_generation_runtime()
        pipeline_factory = build_pipeline
    database = Database(settings.ai_database_url)
    try:
        await database.check_ready()
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
        await GenerationWorker(JobRepository(database, settings), pipeline_factory).run(stop)
    finally:
        await database.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    configure_event_loop()
    asyncio.run(main())

"""Real PostgreSQL locking, fencing, persistence and atomic result tests."""
import asyncio
import json
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from src.jobs.contracts import CreateGenerationRequest
from src.jobs.database import Database
from src.jobs.models import GenerationEvent, GenerationJob
from src.jobs.repository import JobConflict, JobNotFound, LeaseLost
from tests.providers import make_pipeline
from src.schemas.generation import GenerateCvRequest
from src.worker import GenerationWorker
from tests.helpers import request_payload
from tests.providers import FakeProvider
from src.pipeline.generation import CvGenerationPipeline
from src.core.jd_analyzer import JDAnalysisOutput
from src.core.experience_writer import ExperienceRewriteProposals
from src.schemas.generation import GeneratedProject, GeneratedSummary
from src.llm import LLMAuthenticationError, LLMInvalidModelError, LLMSchemaError, LLMTimeoutError

pytestmark = [pytest.mark.postgres, pytest.mark.asyncio]


@pytest.mark.parametrize("schema,cause,stage,code", [
    (JDAnalysisOutput, LLMInvalidModelError, "jd_analysis", "LLM_INVALID_MODEL"),
    (GeneratedSummary, LLMTimeoutError, "summary", "LLM_TIMEOUT"),
    (ExperienceRewriteProposals, LLMAuthenticationError, "experience", "LLM_AUTHENTICATION_ERROR"),
    (GeneratedProject, LLMSchemaError, "projects", "LLM_SCHEMA_ERROR"),
])
async def test_provider_failure_persists_classified_diagnostics_and_no_cv(job_repository, caplog, schema, cause, stage, code):
    from src.api.service import GenerateService
    from src.jobs.service import JobService

    payload = request_payload()
    payload["profile"]["projects"] = [{"id": "proj-1", "name": "API Project", "technologies": ["Python"],
                                        "facts": ["Built Python REST endpoints for an internal project."]}]
    job = await job_repository.create(payload, legacy=True)
    provider = FakeProvider(errors={schema: cause("private-provider-key candidate@example.com")})
    worker = GenerationWorker(job_repository, lambda: CvGenerationPipeline(provider))
    await worker.run_one(await job_repository.claim())
    finished = await job_repository.get(job.id)
    assert finished.status == "FAILED" and finished.result["document"] is None
    assert finished.error["code"] == code and finished.error["stage"] == stage
    assert finished.error["schema"] == schema.__name__
    assert "location" in finished.error
    assert "private-provider-key" not in json.dumps(finished.error) + caplog.text
    assert "candidate@example.com" not in json.dumps(finished.error) + caplog.text
    assert f"stage={stage}" in caplog.text
    events = await job_repository.events(job.id, 0)
    assert events[-1].type == "error" and events[-1].data["code"] == code
    modern = [event async for event in JobService(job_repository).stream(job.id)]
    assert code in modern[-1]
    legacy = [event async for event in GenerateService(job_repository).stream(job.id)]
    assert set(json.loads(legacy[-1].split("data: ", 1)[1])["data"]) == {"message"}


def creation_payload(**overrides):
    data = request_payload(**overrides)
    data.pop("generationId")
    return CreateGenerationRequest.model_validate(data).model_dump(by_alias=True)


async def expire_lease(repository, job_id):
    async with repository.database.sessions.begin() as session:
        await session.execute(update(GenerationJob).where(GenerationJob.id == job_id).values(
            lease_expires_at=func.clock_timestamp() - text("interval '1 second'"),
        ))


async def test_concurrent_create_is_idempotent_and_conflicting_input_rejected(job_repository):
    payload = creation_payload()
    jobs = await asyncio.gather(*(job_repository.create(payload) for _ in range(8)))
    assert len({job.id for job in jobs}) == 1
    normalized = creation_payload()
    normalized["profile"]["name"] = "  Nguyen Van An  "
    assert (await job_repository.create(normalized)).id == jobs[0].id
    with pytest.raises(JobConflict):
        await job_repository.create(creation_payload(jobDescription="Different JD"))
    async with job_repository.database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(GenerationJob)) == 1


async def test_legacy_generation_id_is_preserved_and_cannot_be_rebound(job_repository):
    data = request_payload()
    job = await job_repository.create(data, legacy=True)
    assert job.id != data["generationId"]
    assert job.input_snapshot["generationId"] == "generation-1"
    with pytest.raises(JobConflict):
        await job_repository.create(request_payload(generationId="changed"), legacy=True)
    with pytest.raises(JobConflict):
        await job_repository.create(request_payload(requestId="different"), legacy=True)


async def test_multiple_workers_claim_once_and_skip_locked_jobs(job_repository):
    first = await job_repository.create(creation_payload(requestId="one"))
    second = await job_repository.create(creation_payload(requestId="two"))
    async with job_repository.database.sessions.begin() as locked:
        await locked.scalar(select(GenerationJob).where(GenerationJob.id == first.id).with_for_update())
        claimed = await asyncio.wait_for(job_repository.claim(), timeout=2)
        assert claimed.id == second.id
    claims = await asyncio.gather(*(job_repository.claim() for _ in range(5)))
    assert [job.id for job in claims if job] == [first.id]


async def test_expired_lease_recovery_fences_old_worker_and_preserves_ids(job_repository):
    created = await job_repository.create(creation_payload())
    old = await job_repository.claim()
    request = GenerateCvRequest.model_validate(old.input_snapshot)
    before = await make_pipeline().generate(request)
    await expire_lease(job_repository, old.id)
    await job_repository.maintain()
    new = await job_repository.claim()
    assert new.id == created.id and new.attempt == 2
    assert new.lease_token != old.lease_token
    with pytest.raises(LeaseLost):
        await job_repository.append(old.id, old.lease_token, {"type": "progress", "data": {}})
    with pytest.raises(LeaseLost):
        await job_repository.finish(old.id, old.lease_token, before)
    worker = GenerationWorker(job_repository, make_pipeline)
    await worker.run_one(new)
    finished = await job_repository.get(created.id)
    assert finished.status == "COMPLETED"
    assert finished.result["document"]["cv"]["sections"] == before.document["cv"]["sections"]
    events = await job_repository.events(created.id, 0)
    assert sum(e.type == "done" for e in events) == 1
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))


async def test_deadline_and_attempt_exhaustion_persist_one_failure(job_repository):
    created = await job_repository.create(creation_payload())
    async with job_repository.database.sessions.begin() as session:
        await session.execute(update(GenerationJob).where(GenerationJob.id == created.id).values(
            deadline_at=func.clock_timestamp() - text("interval '1 second'"),
        ))
    await job_repository.maintain()
    await job_repository.maintain()
    finished = await job_repository.get(created.id)
    assert finished.status == "FAILED" and finished.error["code"] == "GENERATION_TIMEOUT"
    assert [e.type for e in await job_repository.events(created.id, 0)] == ["error"]

    another = await job_repository.create(creation_payload(requestId="another"))
    for _ in range(2):
        await job_repository.claim()
        await expire_lease(job_repository, another.id)
        await job_repository.maintain()
    assert (await job_repository.get(another.id)).error["code"] == "ATTEMPTS_EXHAUSTED"
    assert await job_repository.claim() is None


async def test_result_status_and_terminal_event_commit_atomically(job_repository):
    created = await job_repository.create(creation_payload())
    claimed = await job_repository.claim()
    result = await make_pipeline().generate(GenerateCvRequest.model_validate(claimed.input_snapshot))
    original = job_repository._event

    def fail_event(*args, **kwargs):
        raise RuntimeError("simulated persistence failure")

    job_repository._event = fail_event
    try:
        with pytest.raises(RuntimeError):
            await job_repository.finish(claimed.id, claimed.lease_token, result)
    finally:
        job_repository._event = original
    rolled_back = await job_repository.get(created.id)
    assert rolled_back.status == "RUNNING" and rolled_back.result is None
    assert await job_repository.events(created.id, 0) == []
    await job_repository.finish(claimed.id, claimed.lease_token, result)
    async with job_repository.database.sessions.begin() as session:
        session.add(GenerationEvent(job_id=claimed.id, sequence=999, attempt=1, type="error", data={}, created_at=claimed.created_at))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_result_survives_connection_pool_restart_and_cleanup_cascades(job_repository):
    created = await job_repository.create(creation_payload())
    claimed = await job_repository.claim()
    await GenerationWorker(job_repository, make_pipeline).run_one(claimed)
    await job_repository.database.close()
    # A fresh pool has no in-memory knowledge of the first worker/API.
    fresh = Database(job_repository.config.ai_database_url)
    try:
        from src.jobs.repository import JobRepository
        recovered = JobRepository(fresh, job_repository.config)
        finished = await recovered.get(created.id)
        assert finished.status == "COMPLETED" and finished.result["document"]
        assert finished.expires_at - finished.finished_at == timedelta(hours=24)
        assert await recovered.events(created.id, 0)
        async with fresh.sessions.begin() as session:
            await session.execute(update(GenerationJob).where(GenerationJob.id == created.id).values(
                expires_at=func.clock_timestamp() - text("interval '1 second'"),
            ))
        with pytest.raises(JobNotFound):
            await recovered.get(created.id)
        await recovered.maintain()
        async with fresh.sessions() as session:
            assert await session.scalar(select(func.count()).select_from(GenerationEvent)) == 0
        new = await recovered.create(creation_payload())
        assert new.id != created.id
    finally:
        await fresh.close()


async def test_worker_rejects_invalid_document_and_does_not_leak_provider_error(job_repository):
    class BrokenPipeline:
        async def generate(self, request, on_event):
            raise RuntimeError("candidate@example.com secret-provider-key")

    created = await job_repository.create(creation_payload())
    await GenerationWorker(job_repository, BrokenPipeline).run_one(await job_repository.claim())
    finished = await job_repository.get(created.id)
    assert finished.status == "FAILED"
    assert "secret-provider-key" not in json.dumps(finished.result)
    assert finished.result["document"] is None

    class InvalidPipeline:
        async def generate(self, request, on_event):
            result = await make_pipeline().generate(request)
            result.document = {"cv": {"invented": True}}
            return result

    another = await job_repository.create(creation_payload(requestId="invalid"))
    await GenerationWorker(job_repository, InvalidPipeline).run_one(await job_repository.claim())
    assert (await job_repository.get(another.id)).status == "FAILED"


async def test_heartbeat_and_graceful_shutdown_allow_recovery(job_repository):
    started = asyncio.Event()

    class PausedPipeline:
        async def generate(self, request, on_event):
            started.set()
            await asyncio.Event().wait()

    created = await job_repository.create(creation_payload())
    worker = GenerationWorker(job_repository, PausedPipeline)
    await worker.tick()
    await asyncio.wait_for(started.wait(), timeout=2)
    before = (await job_repository.get(created.id)).lease_expires_at
    await asyncio.sleep(job_repository.config.ai_heartbeat_seconds * 3)
    assert (await job_repository.get(created.id)).lease_expires_at > before
    await worker.shutdown()
    await job_repository.maintain()
    claimed = await job_repository.claim()
    assert claimed.id == created.id and claimed.attempt == 2
    await GenerationWorker(job_repository, make_pipeline).run_one(claimed)
    assert (await job_repository.get(created.id)).status == "COMPLETED"


async def test_transient_storage_failure_uses_bounded_recovery(job_repository):
    from sqlalchemy.exc import OperationalError

    class Interrupted:
        async def generate(self, request, on_event):
            raise OperationalError("database interrupted", None, RuntimeError("connection closed"))

    created = await job_repository.create(creation_payload())
    await GenerationWorker(job_repository, Interrupted).run_one(await job_repository.claim())
    assert (await job_repository.get(created.id)).result is None
    assert await job_repository.events(created.id, 0) == []
    await job_repository.maintain()
    claimed = await job_repository.claim()
    assert claimed.attempt == 2
    await GenerationWorker(job_repository, make_pipeline).run_one(claimed)
    assert (await job_repository.get(created.id)).status == "COMPLETED"

"""
Shared Application Service for CV AI Agent.
Powers both synchronous (POST /v1/ai/tailor) and streaming SSE (POST /v1/ai/tailor/stream).
"""
import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional

from ..schemas.canonical_dto import CanonicalTailorRequest, TailorDiffReport
from ..pipeline.agent_orchestrator import AgentTailorPipeline
from ..knowledge.retriever_protocol import KnowledgeRetriever
from ..llm import LLMProvider

logger = logging.getLogger(__name__)


class TailorService:
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        self.pipeline = AgentTailorPipeline(provider=provider, retriever=retriever)

    async def tailor_sync(self, request: CanonicalTailorRequest) -> TailorDiffReport:
        """Runs the pipeline synchronously and returns the complete diff report."""
        start_time = time.perf_counter()
        run_id = request.requestId
        cv_id = request.cvId
        logger.info("Starting sync tailor runId=%s cvId=%s", run_id, cv_id)

        try:
            report = await self.pipeline.tailor_document(request)
            duration = time.perf_counter() - start_time
            logger.info(
                "Completed sync tailor runId=%s status=%s duration=%.3fs acceptedCount=%d",
                run_id,
                report.status,
                duration,
                len(report.acceptedPatches),
            )
            return report
        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.exception("Failed sync tailor runId=%s duration=%.3fs: %s", run_id, duration, exc)
            return TailorDiffReport(
                requestId=run_id,
                cvId=cv_id,
                baseVersion=request.baseVersion,
                status="failed",
                summary=f"Unexpected error: {str(exc)}",
                appliedDocument=None,
            )

    async def tailor_stream(
        self,
        request: CanonicalTailorRequest,
        raw_request: Optional[Any] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the pipeline in a background task and streams standardized SSE envelopes.
        Envelope format:
        {
            "type": "event_name",
            "runId": "uuid",
            "sequence": 1,
            "data": { ... }
        }
        Guarantees exactly one terminal event: 'completed' or 'failed'.
        """
        start_time = time.perf_counter()
        run_id = request.requestId
        cv_id = request.cvId
        sequence = 0
        terminal_emitted = False

        event_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        async def on_progress(event_item: Dict[str, Any]):
            await event_queue.put(event_item)

        tailor_task = asyncio.create_task(
            self.pipeline.tailor_document(request, on_progress=on_progress)
        )

        try:
            while not tailor_task.done() or not event_queue.empty():
                if raw_request is not None and hasattr(raw_request, "is_disconnected"):
                    if await raw_request.is_disconnected():
                        logger.warning("Client disconnect detected, cancelling tailor task runId=%s", run_id)
                        tailor_task.cancel()
                        break

                try:
                    event_item = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    sequence += 1
                    event_type = event_item.get("type", "progress")

                    envelope = {
                        "type": event_type,
                        "runId": run_id,
                        "sequence": sequence,
                        "data": event_item.get("data", {}),
                    }

                    if event_type in ("completed", "failed"):
                        terminal_emitted = True

                    yield {
                        "event": event_type,
                        "data": json.dumps(envelope),
                    }
                except asyncio.TimeoutError:
                    continue

            # Wait for task completion and inspect report
            report = await tailor_task

            if not terminal_emitted:
                sequence += 1
                terminal_event_type = "failed" if report.status == "failed" else "completed"
                envelope = {
                    "type": terminal_event_type,
                    "runId": run_id,
                    "sequence": sequence,
                    "data": report.model_dump(),
                }
                yield {
                    "event": terminal_event_type,
                    "data": json.dumps(envelope),
                }

            duration = time.perf_counter() - start_time
            logger.info("Finished streaming tailor runId=%s duration=%.3fs", run_id, duration)

        except asyncio.CancelledError:
            logger.warning("Client disconnected, cancelling tailor task runId=%s", run_id)
            tailor_task.cancel()
            try:
                await tailor_task
            except (asyncio.CancelledError, Exception):
                pass
            raise

        except Exception as exc:
            logger.exception("Tailor streaming error runId=%s: %s", run_id, exc)
            if not terminal_emitted:
                sequence += 1
                envelope = {
                    "type": "failed",
                    "runId": run_id,
                    "sequence": sequence,
                    "data": {"message": str(exc)},
                }
                yield {
                    "event": "failed",
                    "data": json.dumps(envelope),
                }

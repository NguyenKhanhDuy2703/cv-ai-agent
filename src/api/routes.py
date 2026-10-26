"""
API routes for CV AI Agent.
Exposes:
- POST /v1/ai/tailor (synchronous canonical optimization diff report)
- POST /v1/ai/tailor/stream (real-time SSE streaming for canonical and legacy payloads)
"""
import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Optional, Union
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..schemas.canonical_dto import CanonicalTailorRequest, TailorDiffReport
from ..schemas.cv_input import CvInput
from ..pipeline.orchestrator import CvTailorPipeline
from .auth import verify_service_bearer
from .service import TailorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/ai", tags=["AI"])


def _get_tailor_service() -> TailorService:
    return TailorService()


class LegacyTailorRequest(BaseModel):
    """Legacy envelope request allowing wrapped CvInput or raw YAML/MD string."""
    cv_input: Optional[CvInput] = None
    raw_text: Optional[str] = None

    def get_cv_input(self) -> CvInput:
        if self.cv_input:
            return self.cv_input
        if self.raw_text:
            from ..yaml_layer.io import load_cv_input_from_text
            return load_cv_input_from_text(self.raw_text)
        raise ValueError("Must provide either 'cv_input' or 'raw_text'.")


@router.post(
    "/tailor",
    response_model=TailorDiffReport,
    summary="Synchronous CV Tailoring",
    dependencies=[Depends(verify_service_bearer)],
)
async def tailor_cv_sync(
    payload: CanonicalTailorRequest,
    service: TailorService = Depends(_get_tailor_service),
) -> TailorDiffReport:
    """
    Synchronously tailors candidate Experience bullets against the target JD.
    Returns structured proposals, semantic patches, and diff report.
    """
    return await service.tailor_sync(payload)


@router.post(
    "/tailor/stream",
    summary="Real-time SSE Streaming CV Tailoring",
    dependencies=[Depends(verify_service_bearer)],
)
async def tailor_cv_stream(
    payload: Union[CanonicalTailorRequest, LegacyTailorRequest, CvInput],
    raw_request: Request,
    service: TailorService = Depends(_get_tailor_service),
):
    """
    Real-time SSE streaming tailor endpoint.
    Supports both CanonicalTailorRequest (Render contract) and legacy CvInput/raw_text.
    """
    # 1. Canonical Render contract flow
    if isinstance(payload, CanonicalTailorRequest):
        generator = service.tailor_stream(payload, raw_request=raw_request)
        return EventSourceResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 2. Legacy flow (for backwards compatibility with previous tests/clients)
    if isinstance(payload, CvInput):
        target_input = payload
    else:
        target_input = payload.get_cv_input()

    event_queue: asyncio.Queue = asyncio.Queue()

    async def progress_hook(event_data: dict):
        await event_queue.put(event_data)

    async def legacy_sse_generator() -> AsyncGenerator[dict, None]:
        pipeline = CvTailorPipeline()
        tailor_task = asyncio.create_task(
            pipeline.tailor(target_input, on_progress=progress_hook)
        )

        while not tailor_task.done() or not event_queue.empty():
            try:
                event_data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                event_name = event_data.get("step", "progress")
                yield {
                    "event": event_name,
                    "data": json.dumps(event_data),
                }
            except asyncio.TimeoutError:
                continue

        try:
            cv_yaml, report, tailored_cv = await tailor_task
            yield {
                "event": "done",
                "data": json.dumps({
                    "status": "success",
                    "cv_yaml": cv_yaml,
                    "report": report.model_dump(),
                    "tailored_cv": tailored_cv.model_dump(),
                }),
            }
        except Exception as exc:
            logger.exception("Tailor streaming error: %s", exc)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(exc)}),
            }

    return EventSourceResponse(
        legacy_sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform"},
    )

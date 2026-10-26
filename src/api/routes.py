"""Backend-only API for stateless canonical CV generation."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..schemas.generation import GenerateCvRequest
from .auth import verify_service_bearer
from .service import GenerateService

router = APIRouter(prefix="/v1/ai", tags=["AI"])


def _get_generate_service() -> GenerateService:
    return GenerateService()


@router.post(
    "/generate/stream",
    summary="Generate a new canonical CV with SSE progress",
    dependencies=[Depends(verify_service_bearer)],
)
async def generate_cv_stream(
    payload: GenerateCvRequest,
    service: GenerateService = Depends(_get_generate_service),
) -> StreamingResponse:
    return StreamingResponse(
        service.stream(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

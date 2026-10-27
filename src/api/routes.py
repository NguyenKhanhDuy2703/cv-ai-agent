"""Service-to-service durable generation APIs and legacy stream adapter."""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from ..jobs.contracts import CreateGenerationRequest, JobEventView, JobView
from ..jobs.models import TERMINAL_STATUSES
from ..jobs.repository import JobRepository
from ..jobs.service import JobService
from ..schemas.generation import GenerateCvRequest, GenerateCvResult
from .auth import verify_service_bearer
from .service import GenerateService

router = APIRouter(prefix="/v1/ai", tags=["AI"], dependencies=[Depends(verify_service_bearer)])
STREAM_HEADERS = {"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"}


def get_repository(request: Request) -> JobRepository:
    repository = getattr(request.app.state, "job_repository", None)
    if repository is None:
        raise HTTPException(503, "AI job storage is unavailable")
    return repository


Repository = Annotated[JobRepository, Depends(get_repository)]


@router.post("/generations", status_code=202, response_model=JobView)
async def create_generation(payload: CreateGenerationRequest, response: Response, repository: Repository):
    job = await repository.create(payload.model_dump(by_alias=True))
    view = JobService(repository).view(job)
    response.headers["Location"] = view.status_url
    response.headers["Retry-After"] = "1"
    return view


@router.get("/generations/{job_id}", response_model=JobView)
async def get_generation(job_id: str, repository: Repository):
    return JobService(repository).view(await repository.get(job_id))


@router.get("/generations/{job_id}/result", response_model=GenerateCvResult)
async def get_generation_result(job_id: str, repository: Repository):
    job = await repository.get(job_id)
    if job.status not in TERMINAL_STATUSES:
        raise HTTPException(409, "Generation has not finished")
    return job.result


@router.get("/generations/{job_id}/events", responses={200: {
    "description": "Persisted SSE events; envelope: type, jobId, requestId, generationId, sequence, attempt, data",
    "content": {"text/event-stream": {"schema": {"type": "string"}}},
}}, openapi_extra={"x-sse-event-schema": JobEventView.model_json_schema(by_alias=True)})
async def generation_events(
    job_id: str, repository: Repository,
    last_event_id: Annotated[str, Header(alias="Last-Event-ID")] = "0",
):
    if not last_event_id.isascii() or not last_event_id.isdigit() or len(last_event_id) > 18:
        raise HTTPException(422, "Last-Event-ID must be a non-negative integer")
    after = int(last_event_id)
    service = JobService(repository)
    await service.check_cursor(job_id, after)
    return StreamingResponse(service.stream(job_id, after=after), media_type="text/event-stream", headers=STREAM_HEADERS)


@router.post("/generate/stream", summary="Legacy stream backed by a durable job")
async def generate_cv_stream(payload: GenerateCvRequest, repository: Repository):
    service = GenerateService(repository)
    job = await service.create(payload)
    return StreamingResponse(service.stream(job.id), media_type="text/event-stream", headers=STREAM_HEADERS)

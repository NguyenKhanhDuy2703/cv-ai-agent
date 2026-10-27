"""Durable SSE and legacy adapter regression tests against real PostgreSQL."""
import asyncio
import json

import pytest

from src.api.service import GenerateService
from src.jobs.service import JobService
from tests.providers import make_pipeline
from src.schemas.generation import GenerateCvRequest
from src.worker import GenerationWorker
from tests.helpers import request_payload

pytestmark = [pytest.mark.postgres, pytest.mark.asyncio]


async def collect(repository, payload):
    service = GenerateService(repository)
    job = await service.create(GenerateCvRequest.model_validate(payload))
    await GenerationWorker(repository, make_pipeline).run_one(await repository.claim())
    return [event async for event in service.stream(job.id)]


async def test_generate_stream_event_order_and_single_terminal_event(job_repository):
    chunks = await collect(job_repository, request_payload())
    events = [chunk.splitlines()[0].removeprefix("event: ") for chunk in chunks]
    assert events[0] == "progress"
    assert events[-1] == "done"
    assert sum(event in {"needs_input", "done", "error"} for event in events) == 1
    assert "Normalizing the candidate profile." in "".join(chunks)
    for sequence, chunk in enumerate(chunks, start=1):
        data = json.loads(chunk.split("data: ", 1)[1])
        assert set(data) == {"type", "requestId", "generationId", "sequence", "data"}
        assert data["generationId"] == "generation-1"
        assert data["sequence"] == sequence
    # Repeating a legacy request replays; no second pipeline run is queued.
    replay = await collect_existing(job_repository, request_payload())
    assert replay == chunks
    assert await job_repository.claim() is None


async def collect_existing(repository, payload):
    service = GenerateService(repository)
    job = await service.create(GenerateCvRequest.model_validate(payload))
    return [event async for event in service.stream(job.id)]


async def test_missing_input_ends_with_needs_input_without_questions_or_done(job_repository):
    payload = request_payload(jobDescription="")
    payload["options"]["language"] = "vi"
    payload["profile"]["name"] = ""
    chunks = await collect(job_repository, payload)
    content = "".join(chunks)
    assert "Normalizing the candidate profile." in content
    assert "Họ và tên đầy đủ" in content
    assert content.count("event: needs_input") == 1
    assert "event: done" not in content
    assert "event: question" not in content


async def test_disconnect_does_not_cancel_job_and_reconnect_replays(job_repository):
    proceed = asyncio.Event()
    started = asyncio.Event()
    cancelled = asyncio.Event()

    class SlowPipeline:
        async def generate(self, request, on_event):
            await on_event({"type": "progress", "data": {"step": "start", "message": "Starting."}})
            started.set()
            try:
                await proceed.wait()
                return await make_pipeline().generate(request, on_event)
            except asyncio.CancelledError:
                cancelled.set()
                raise

    service = GenerateService(job_repository)
    job = await service.create(GenerateCvRequest.model_validate(request_payload()))
    worker = GenerationWorker(job_repository, SlowPipeline)
    task = asyncio.create_task(worker.run_one(await job_repository.claim()))
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        stream = service.stream(job.id)
        assert "event: progress" in await stream.__anext__()
        await stream.aclose()
        assert not cancelled.is_set() and not task.done()
        assert (await job_repository.get(job.id)).status == "RUNNING"
        proceed.set()
        await asyncio.wait_for(task, timeout=5)
        events = [chunk async for chunk in JobService(job_repository).stream(job.id, after=1)]
        assert events[0].startswith("id: 2\n")
        assert events[-1].find("event: done") != -1
        assert (await job_repository.get(job.id)).status == "COMPLETED"
        last = (await job_repository.get(job.id)).last_sequence
        assert [chunk async for chunk in JobService(job_repository).stream(job.id, after=last)] == []
    finally:
        proceed.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_sse_heartbeat_without_processing(job_repository):
    job_repository.config.ai_sse_heartbeat_seconds = 0.01
    service = GenerateService(job_repository)
    job = await service.create(GenerateCvRequest.model_validate(request_payload()))
    stream = service.jobs.stream(job.id)
    assert await asyncio.wait_for(stream.__anext__(), timeout=2) == ": keep-alive\n\n"
    await stream.aclose()
    assert (await job_repository.get(job.id)).status == "QUEUED"

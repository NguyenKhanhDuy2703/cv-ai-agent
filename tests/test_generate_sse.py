import asyncio

import pytest

from src.api.service import GenerateService
from src.llm.mock_provider import MockProvider
from src.schemas.generation import GenerateCvRequest
from tests.helpers import request_payload


class SlowPipeline:
    def __init__(self):
        self.cancelled = asyncio.Event()

    async def generate(self, request, on_event):
        await on_event({"type": "progress", "data": {"step": "start", "message": "Starting."}})
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


async def collect(payload):
    request = GenerateCvRequest.model_validate(payload)
    service = GenerateService(provider=MockProvider())
    return [event async for event in service.stream(request)]


@pytest.mark.asyncio
async def test_generate_stream_event_order_and_single_terminal_event():
    chunks = await collect(request_payload())
    events = [chunk.splitlines()[0].removeprefix("event: ") for chunk in chunks]
    assert events[0] == "progress"
    assert events[-1] == "done"
    assert sum(event in {"needs_input", "done", "error"} for event in events) == 1
    assert "Normalizing the candidate profile." in "".join(chunks)


@pytest.mark.asyncio
async def test_missing_input_ends_with_needs_input_without_questions_or_done():
    payload = request_payload(jobDescription="")
    payload["options"]["language"] = "vi"
    payload["profile"]["name"] = ""
    chunks = await collect(payload)
    content = "".join(chunks)
    assert "Normalizing the candidate profile." in content
    assert "Họ và tên đầy đủ" in content
    assert content.count("event: needs_input") == 1
    assert "event: done" not in content
    assert "event: question" not in content


@pytest.mark.asyncio
async def test_backend_upstream_cancellation_releases_ai_task():
    service = GenerateService(provider=MockProvider())
    slow = SlowPipeline()
    service.pipeline = slow
    stream = service.stream(GenerateCvRequest.model_validate(request_payload()))
    assert "event: progress" in await stream.__anext__()
    await stream.aclose()
    await asyncio.wait_for(slow.cancelled.wait(), timeout=1)

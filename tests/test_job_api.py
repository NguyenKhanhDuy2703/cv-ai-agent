"""HTTP contract, auth, status/result and replay integration."""
import asyncio
import json

import httpx
import pytest

from src.api.routes import get_repository
from src.api.server import app
from src.config import settings
from tests.providers import make_pipeline
from src.worker import GenerationWorker
from tests.helpers import request_payload

pytestmark = [pytest.mark.postgres, pytest.mark.asyncio]


def payload():
    result = request_payload()
    result.pop("generationId")
    return result


@pytest.fixture
def api_client(job_repository, monkeypatch):
    monkeypatch.setattr(settings, "ai_secret_key", "test-service-token")
    app.dependency_overrides[get_repository] = lambda: job_repository
    try:
        yield httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ai",
                                headers={"Authorization": "Bearer test-service-token"})
    finally:
        app.dependency_overrides.clear()


async def test_http_create_lookup_result_and_replay(api_client, job_repository):
    async with api_client as client:
        response = await client.post("/v1/ai/generations", json=payload())
        assert response.status_code == 202
        job = response.json()
        assert job["status"] == "QUEUED" and job["attempt"] == 0
        assert response.headers["Location"] == job["statusUrl"]
        assert (await client.get(job["resultUrl"])).status_code == 409
        assert (await client.get("/v1/ai/generations/not-found")).status_code == 404
        assert (await client.post("/v1/ai/generations", json=payload())).json()["jobId"] == job["jobId"]
        changed = payload()
        changed["jobDescription"] = "changed"
        assert (await client.post("/v1/ai/generations", json=changed)).status_code == 409
        await GenerationWorker(job_repository, make_pipeline).run_one(await job_repository.claim())
        status = (await client.get(job["statusUrl"])).json()
        assert status["status"] == "COMPLETED" and status["attempt"] == 1
        result = (await client.get(job["resultUrl"])).json()
        assert result["document"] and result["cvYaml"].startswith("cv:")
        events = await client.get(job["eventsUrl"])
        assert events.headers["content-type"].startswith("text/event-stream")
        assert "id: 1\nevent: progress" in events.text
        assert events.text.count("event: done") == 1
        assert '"cvId"' not in events.text
        envelope = json.loads(events.text.split("data: ", 1)[1].splitlines()[0])
        assert envelope["attempt"] == 1 and envelope["jobId"] == job["jobId"]
        replay = await client.get(job["eventsUrl"], headers={"Last-Event-ID": str(status["lastSequence"])})
        assert replay.status_code == 200 and replay.text == ""
        assert (await client.get(job["eventsUrl"], headers={"Last-Event-ID": "99999"})).status_code == 409
        assert (await client.get(job["eventsUrl"], headers={"Last-Event-ID": "-1"})).status_code == 422


async def test_auth_validation_and_readiness(api_client, job_repository, monkeypatch):
    async with api_client as client:
        for method, url in [("POST", "/v1/ai/generations"), ("GET", "/v1/ai/generations/missing"),
                            ("GET", "/v1/ai/generations/missing/events"), ("GET", "/v1/ai/generations/missing/result"),
                            ("POST", "/v1/ai/generate/stream")]:
            assert (await client.request(method, url, headers={"Authorization": "Bearer wrong"}, json={})).status_code == 401
        invalid = payload()
        invalid["profile"]["experiences"][0]["facts"] = "not a list"
        assert (await client.post("/v1/ai/generations", json=invalid)).status_code == 422
        assert await job_repository.claim() is None
        monkeypatch.setattr(app.state, "database", job_repository.database, raising=False)
        assert (await client.get("/health/ready")).status_code == 200
        async with job_repository.database.engine.begin() as connection:
            from sqlalchemy import text
            await connection.execute(text("UPDATE alembic_version SET version_num='outdated'"))
        try:
            assert (await client.get("/health/ready")).status_code == 503
        finally:
            async with job_repository.database.engine.begin() as connection:
                await connection.execute(text("UPDATE alembic_version SET version_num='0001_generation_jobs'"))


async def test_legacy_http_contract_survives_adapter(api_client, job_repository):
    from src.api.service import GenerateService
    from src.schemas.generation import GenerateCvRequest

    old = request_payload()
    await GenerateService(job_repository).create(GenerateCvRequest.model_validate(old))
    await GenerationWorker(job_repository, make_pipeline).run_one(await job_repository.claim())
    async with api_client as client:
        response = await client.post("/v1/ai/generate/stream", json=old)
        assert response.status_code == 200
        assert response.text.startswith("event: progress\n")
        assert response.text.count("event: done") == 1
        assert '"generationId": "generation-1"' in response.text
        assert '"jobId"' not in response.text


async def test_status_settles_deadline_without_a_running_worker(api_client, job_repository):
    from sqlalchemy import func, text, update
    from src.jobs.models import GenerationJob

    async with api_client as client:
        job = (await client.post("/v1/ai/generations", json=payload())).json()
        async with job_repository.database.sessions.begin() as session:
            await session.execute(update(GenerationJob).where(GenerationJob.id == job["jobId"]).values(
                deadline_at=func.clock_timestamp() - text("interval '1 second'"),
            ))
        responses = await asyncio.gather(*(client.get(job["statusUrl"]) for _ in range(4)))
        assert all(response.json()["status"] == "FAILED" for response in responses)
        assert responses[0].json()["error"]["code"] == "GENERATION_TIMEOUT"
        assert (await client.get(job["resultUrl"])).json()["status"] == "failed"
        events = await job_repository.events(job["jobId"], 0)
        assert [event.type for event in events] == ["error"]

"""Contracts and readiness remain testable without a running PostgreSQL server."""
import httpx
import pytest
from pydantic import ValidationError

from src.api.server import app
from src.jobs.contracts import CreateGenerationRequest
from src.jobs.database import database_url
from tests.helpers import request_payload


def test_new_job_request_does_not_accept_client_generation_id_or_conversation():
    payload = request_payload()
    with pytest.raises(ValidationError):
        CreateGenerationRequest.model_validate(payload)
    payload.pop("generationId")
    request = CreateGenerationRequest.model_validate(payload)
    assert request.profile.experiences[0].id == "exp-client-1"
    with pytest.raises(ValidationError):
        CreateGenerationRequest.model_validate({**payload, "history": []})
    with pytest.raises(ValidationError):
        CreateGenerationRequest.model_validate({**payload, "requestId": " "})


def test_postgres_url_required_only_when_database_component_is_constructed():
    assert database_url("postgresql://user:password@localhost/ai") == "postgresql+psycopg://user:password@localhost/ai"
    for value in ("", "sqlite:///test.db", "postgresql+asyncpg://localhost/ai"):
        with pytest.raises(ValueError):
            database_url(value)


@pytest.mark.asyncio
async def test_readiness_unavailable_database_returns_503_without_exposing_error(monkeypatch):
    class Unavailable:
        async def check_ready(self):
            raise RuntimeError("database password is confidential")

    monkeypatch.setattr(app.state, "database", Unavailable(), raising=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ai") as client:
        response = await client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready"}
        assert (await client.get("/health/live")).status_code == 200


def test_openapi_advertises_new_and_legacy_routes_and_python_contract():
    schema = app.openapi()
    assert "/v1/ai/generate/stream" in schema["paths"]
    assert schema["paths"]["/v1/ai/generations"]["post"]["responses"]["202"]
    assert "CreateGenerationRequest" in schema["components"]["schemas"]
    assert "JobView" in schema["components"]["schemas"]
    event_schema = schema["paths"]["/v1/ai/generations/{job_id}/events"]["get"]["x-sse-event-schema"]
    assert "attempt" in event_schema["properties"]

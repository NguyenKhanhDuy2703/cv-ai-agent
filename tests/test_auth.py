import pytest
from fastapi import HTTPException

from src.api.auth import verify_service_bearer
from src.config import settings


@pytest.mark.asyncio
async def test_service_bearer_rejects_missing_and_invalid_tokens(monkeypatch):
    monkeypatch.setattr(settings, "ai_secret_key", "backend-secret")
    with pytest.raises(HTTPException) as missing:
        await verify_service_bearer(None)
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as invalid:
        await verify_service_bearer("Bearer wrong")
    assert invalid.value.status_code == 401


@pytest.mark.asyncio
async def test_service_bearer_accepts_backend_token(monkeypatch):
    monkeypatch.setattr(settings, "ai_secret_key", "backend-secret")
    assert await verify_service_bearer("Bearer backend-secret") is True

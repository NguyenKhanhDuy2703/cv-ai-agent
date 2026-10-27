"""Production has no fake mode; failures identify their stage without leaking data."""
import logging
import os
import subprocess
import sys

import pytest

from src.core.jd_analyzer import JDAnalysisOutput
from src.llm import LLMAuthenticationError, LLMInvalidModelError, LLMUnavailableError
from src.llm.operations import GenerationStepError, JOB_CONTEXT, generate_at_stage, safe_error_details
from tests.providers import FakeProvider


@pytest.mark.asyncio
async def test_stage_error_preserves_safe_debug_metadata():
    error = LLMAuthenticationError("private-key candidate@example.com")
    provider = FakeProvider(errors={JDAnalysisOutput: error})
    with pytest.raises(GenerationStepError) as failure:
        await generate_at_stage(provider, JDAnalysisOutput, [], "jd_analysis")
    details = safe_error_details(failure.value)
    assert details["stage"] == "jd_analysis"
    assert details["code"] == "LLM_AUTHENTICATION_ERROR"
    assert details["errorType"] == "LLMAuthenticationError"
    assert details["schema"] == "JDAnalysisOutput"
    assert details["location"].startswith("src/llm/operations.py:")
    assert "private-key" not in str(details) and "candidate@example.com" not in str(details)


def test_factory_selects_gemini_and_requires_explicit_credentials(monkeypatch):
    from src.config import ConfigurationError
    from src.llm import factory
    from src.llm import gemini_provider

    monkeypatch.setattr(factory.settings, "ai_provider", "gemini")
    monkeypatch.setattr(factory.settings, "ai_api_key", "")
    with pytest.raises(ConfigurationError, match="AI_API_KEY"):
        factory.get_llm_provider()
    monkeypatch.setattr(factory.settings, "ai_api_key", "test-key")
    monkeypatch.setattr(factory.settings, "ai_model", "test-model")
    captured = {}

    def configured(**kwargs):
        captured.update(kwargs)
        return "provider-instance"

    monkeypatch.setattr(gemini_provider, "GeminiProvider", configured)
    assert factory.get_llm_provider() == "provider-instance"
    assert captured == {"api_key": "test-key", "model": "test-model"}


def test_provider_has_no_implicit_model_or_empty_key():
    from src.llm.gemini_provider import GeminiProvider

    with pytest.raises(LLMInvalidModelError):
        GeminiProvider(api_key="test-key", model="", client=object())
    with pytest.raises(LLMAuthenticationError):
        GeminiProvider(api_key="", model="test-model", client=object())


@pytest.mark.asyncio
async def test_project_source_mismatch_has_a_safe_writer_location():
    from src.core.evidence_extractor import EvidenceStore
    from src.pipeline.generation.writers import ProjectWriter
    from src.schemas.generation import GeneratedProject

    provider = FakeProvider()
    provider.set_response(GeneratedProject, GeneratedProject(sourceId="wrong-id", highlights=[], evidenceIds=[]))
    with pytest.raises(GenerationStepError) as failure:
        await ProjectWriter(provider).write(
            "project-1", "API Project", ["Built an API."], ["Python"],
            JDAnalysisOutput(role_family="Backend", seniority="Senior"), EvidenceStore(items=[]), [], "en",
        )
    details = safe_error_details(failure.value)
    assert details["code"] == "LLM_SCHEMA_ERROR" and details["sourceId"] == "project-1"
    assert details["location"].startswith("src/pipeline/generation/writers.py:")


def test_worker_fails_before_processing_when_credentials_missing():
    result = subprocess.run(
        [sys.executable, "-B", "-m", "src.worker"],
        env={**os.environ, "AI_PROVIDER": "gemini", "AI_API_KEY": "", "AI_MODEL": ""},
        capture_output=True, text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    assert result.returncode != 0
    assert "AI_API_KEY is required" in result.stderr


@pytest.mark.asyncio
async def test_retry_logs_context_without_raw_provider_message(caplog):
    from unittest.mock import AsyncMock, MagicMock
    from src.llm.gemini_provider import GeminiProvider
    from src.schemas.generation import GeneratedSummary
    from google.genai import errors

    key = "sensitive-provider-key"
    call = AsyncMock(side_effect=errors.ServerError(503, {"error": {"code": 503,
                     "message": f"{key} candidate@example.com", "status": "UNAVAILABLE"}}))
    client = MagicMock()
    client.aio.models.generate_content = call
    provider = GeminiProvider(api_key=key, model="test-model", client=client)
    token = JOB_CONTEXT.set({"jobId": "job-123", "requestId": "request-456"})
    try:
        with caplog.at_level(logging.WARNING), pytest.raises(LLMUnavailableError):
            await provider.generate_structured(GeneratedSummary, [])
    finally:
        JOB_CONTEXT.reset(token)
    assert call.call_count == 3
    assert "jobId=job-123" in caplog.text and "requestId=request-456" in caplog.text
    assert key not in caplog.text and "candidate@example.com" not in caplog.text

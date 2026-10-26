"""
Unit tests for GeminiProvider error classification, fast-fail behavior,
bounded retries on transient errors, and API key sanitization.

All tests use mocked responses and do not make real network calls.
"""
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from pydantic import BaseModel
from google.genai import errors as genai_errors

from src.llm import (
    GenerateOpts,
    LLMAuthenticationError,
    LLMClientError,
    LLMInvalidModelError,
    LLMNetworkError,
    LLMRateLimitError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from src.llm.gemini_provider import GeminiProvider


class DummyResponseSchema(BaseModel):
    message: str
    score: int


def _make_mock_client(generate_content_func: AsyncMock) -> MagicMock:
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    client.aio.models.generate_content = generate_content_func
    return client


class TestGeminiProvider:
    @pytest.mark.asyncio
    async def test_successful_structured_generation(self):
        """Happy path: Gemini returns valid JSON matching the requested schema."""
        mock_response = MagicMock()
        mock_response.text = '{"message": "Hello world", "score": 95}'

        mock_call = AsyncMock(return_value=mock_response)
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)
        result = await provider.generate_structured(
            schema=DummyResponseSchema,
            messages=[{"role": "user", "content": "test"}],
        )

        assert isinstance(result, DummyResponseSchema)
        assert result.message == "Hello world"
        assert result.score == 95
        assert mock_call.call_count == 1

    @pytest.mark.asyncio
    async def test_invalid_model_fails_fast_without_retrying(self):
        """404 Not Found (invalid model ID) must fail immediately with LLMInvalidModelError."""
        error_404 = genai_errors.ClientError(
            404,
            {
                "error": {
                    "code": 404,
                    "message": "models/non-existent-model is not found for API version v1beta",
                    "status": "NOT_FOUND",
                }
            },
        )
        mock_call = AsyncMock(side_effect=error_404)
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="non-existent-model", client=client)

        with pytest.raises(LLMInvalidModelError) as exc_info:
            await provider.generate_structured(
                schema=DummyResponseSchema,
                messages=[{"role": "user", "content": "test"}],
            )

        # Must fail immediately on attempt 1 (no retries)
        assert mock_call.call_count == 1
        assert "non-existent-model" in str(exc_info.value)
        assert "HTTP 404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_error_fails_fast_without_retrying(self):
        """403 Permission Denied / 401 Unauthorized must fail immediately with LLMAuthenticationError."""
        error_403 = genai_errors.ClientError(
            403,
            {
                "error": {
                    "code": 403,
                    "message": "API key not valid. Please pass a valid API key.",
                    "status": "PERMISSION_DENIED",
                }
            },
        )
        mock_call = AsyncMock(side_effect=error_403)
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)

        with pytest.raises(LLMAuthenticationError) as exc_info:
            await provider.generate_structured(
                schema=DummyResponseSchema,
                messages=[{"role": "user", "content": "test"}],
            )

        # Must fail immediately on attempt 1 (no retries)
        assert mock_call.call_count == 1
        assert "authentication failed" in str(exc_info.value).lower()
        assert "AI_API_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_client_bad_request_fails_fast(self):
        """400 Bad Request must fail immediately with LLMClientError."""
        error_400 = genai_errors.ClientError(
            400,
            {
                "error": {
                    "code": 400,
                    "message": "Invalid generation configuration parameter",
                    "status": "INVALID_ARGUMENT",
                }
            },
        )
        mock_call = AsyncMock(side_effect=error_400)
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)

        with pytest.raises(LLMClientError) as exc_info:
            await provider.generate_structured(
                schema=DummyResponseSchema,
                messages=[{"role": "user", "content": "test"}],
            )

        assert mock_call.call_count == 1
        assert "HTTP 400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_schema_mismatch_fails_fast(self):
        """If response text does not conform to the Pydantic schema, fail fast with LLMSchemaError."""
        mock_response = MagicMock()
        mock_response.text = '{"unexpected_field": "test"}'  # missing required fields

        mock_call = AsyncMock(return_value=mock_response)
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)

        with pytest.raises(LLMSchemaError):
            await provider.generate_structured(
                schema=DummyResponseSchema,
                messages=[{"role": "user", "content": "test"}],
            )

        assert mock_call.call_count == 1

    @pytest.mark.asyncio
    async def test_transient_503_unavailable_retries_and_succeeds(self):
        """503 Service Unavailable / Model Overloaded retries and succeeds if recovered."""
        error_503 = genai_errors.ServerError(
            503,
            {
                "error": {
                    "code": 503,
                    "message": "The model is overloaded. Please try again later.",
                    "status": "UNAVAILABLE",
                }
            },
        )
        mock_response = MagicMock()
        mock_response.text = '{"message": "Recovered", "score": 100}'

        # Fail once with 503, succeed on second attempt
        mock_call = AsyncMock(side_effect=[error_503, mock_response])
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)
        result = await provider.generate_structured(
            schema=DummyResponseSchema,
            messages=[{"role": "user", "content": "test"}],
        )

        assert result.message == "Recovered"
        assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_transient_503_unavailable_exhausts_bounded_retries(self):
        """503 Service Unavailable is bounded by _MAX_RETRIES (3 attempts), then raises LLMUnavailableError."""
        error_503 = genai_errors.ServerError(
            503,
            {
                "error": {
                    "code": 503,
                    "message": "The model is overloaded. Please try again later.",
                    "status": "UNAVAILABLE",
                }
            },
        )
        mock_call = AsyncMock(side_effect=error_503)
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)

        with pytest.raises(LLMUnavailableError) as exc_info:
            await provider.generate_structured(
                schema=DummyResponseSchema,
                messages=[{"role": "user", "content": "test"}],
            )

        # Bounded at 3 attempts
        assert mock_call.call_count == 3
        assert "temporarily unavailable" in str(exc_info.value).lower()
        assert "HTTP 503" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limit_429_retries_and_recovers(self):
        """429 Rate Limit / Resource Exhausted is considered transient and retried."""
        error_429 = genai_errors.ClientError(
            429,
            {
                "error": {
                    "code": 429,
                    "message": "Resource has been exhausted (e.g. check quota).",
                    "status": "RESOURCE_EXHAUSTED",
                }
            },
        )
        mock_response = MagicMock()
        mock_response.text = '{"message": "Rate limit cleared", "score": 88}'

        mock_call = AsyncMock(side_effect=[error_429, mock_response])
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)
        result = await provider.generate_structured(
            schema=DummyResponseSchema,
            messages=[{"role": "user", "content": "test"}],
        )

        assert result.message == "Rate limit cleared"
        assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_network_connection_error_retries_and_recovers(self):
        """httpx.ConnectError is transient and retried."""
        net_error = httpx.ConnectError("Connection refused by peer")
        mock_response = MagicMock()
        mock_response.text = '{"message": "Connection re-established", "score": 90}'

        mock_call = AsyncMock(side_effect=[net_error, mock_response])
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key="secret-key-123", model="gemini-2.0-flash", client=client)
        result = await provider.generate_structured(
            schema=DummyResponseSchema,
            messages=[{"role": "user", "content": "test"}],
        )

        assert result.message == "Connection re-established"
        assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_api_key_is_never_leaked_in_exception_messages(self):
        """Sensitive API key must be sanitized from error strings."""
        sensitive_key = "MY_SUPER_SECRET_KEY_9999"
        error_with_key = genai_errors.ClientError(
            403,
            {
                "error": {
                    "code": 403,
                    "message": f"Invalid key: {sensitive_key} is not authorized",
                    "status": "PERMISSION_DENIED",
                }
            },
        )
        mock_call = AsyncMock(side_effect=error_with_key)
        client = _make_mock_client(mock_call)

        provider = GeminiProvider(api_key=sensitive_key, model="gemini-2.0-flash", client=client)

        with pytest.raises(LLMAuthenticationError) as exc_info:
            await provider.generate_structured(
                schema=DummyResponseSchema,
                messages=[{"role": "user", "content": "test"}],
            )

        err_msg = str(exc_info.value)
        assert sensitive_key not in err_msg
        assert "[REDACTED_API_KEY]" in err_msg

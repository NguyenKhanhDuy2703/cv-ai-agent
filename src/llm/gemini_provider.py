"""
Gemini LLM provider using the modern official google-genai SDK.

Requires:
  AI_PROVIDER=gemini
  AI_API_KEY=<your Gemini API key>
  AI_MODEL=<an enabled model ID for your account>

Uses Gemini's native structured output (response_mime_type + response_schema)
so the response is always valid JSON matching the requested Pydantic schema.

Error handling:
  - Distinguishes authentication, invalid model, rate-limit, and transient server errors.
  - Retries ONLY transient/retryable errors with bounded exponential backoff.
  - Fails fast on permanent client errors (401, 403, 404, 400).
  - Sanitizes all error messages to never leak API keys.
"""
import asyncio
import json
import logging
from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from . import (
    GenerateOpts,
    LLMAuthenticationError,
    LLMClientError,
    LLMError,
    LLMInvalidModelError,
    LLMNetworkError,
    LLMRateLimitError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMUnavailableError,
    RETRYABLE_LLM_ERRORS,
)
from .operations import JOB_CONTEXT

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

import os

_MAX_RETRIES = 3
_RETRY_MIN_WAIT = float(os.getenv("LLM_RETRY_MIN_WAIT", "1.0"))
_RETRY_MAX_WAIT = float(os.getenv("LLM_RETRY_MAX_WAIT", "8.0"))


def _log_retry_attempt(retry_state: Any) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    next_wait = getattr(retry_state.next_action, "sleep", 0) if retry_state.next_action else 0
    logger.warning(
        "Gemini retry jobId=%s requestId=%s jobAttempt=%s providerAttempt=%d/%d errorType=%s waitSeconds=%.1f",
        JOB_CONTEXT.get().get("jobId", "unknown"),
        JOB_CONTEXT.get().get("requestId", "unknown"),
        JOB_CONTEXT.get().get("attempt", "unknown"),
        attempt,
        _MAX_RETRIES,
        type(exc).__name__,
        next_wait,
    )


class GeminiProvider:
    """
    Calls the Gemini API and returns a validated Pydantic model.
    Enforces structured output, bounded retries on transient errors,
    and fast-fail on permanent errors with key sanitization.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Optional[Any] = None,
    ) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ImportError(
                "google-genai is required for GeminiProvider. "
                "Install it: pip install google-genai"
            ) from exc

        if not api_key or not api_key.strip():
            raise LLMAuthenticationError("AI_API_KEY is required")
        if not model or not model.strip():
            raise LLMInvalidModelError("AI_MODEL is required")
        self._api_key = api_key
        self._types = types
        self._model_name = model

        if client is not None:
            self._client = client
        else:
            self._client = genai.Client(api_key=self._api_key)

    def __repr__(self) -> str:
        return f"GeminiProvider(model='{self._model_name}')"

    def _sanitize(self, text: str) -> str:
        """Strip API key from error strings to prevent accidental leakage in logs."""
        if self._api_key and self._api_key in text:
            text = text.replace(self._api_key, "[REDACTED_API_KEY]")
        return text

    def _classify_error(self, exc: Exception) -> Exception:
        """
        Classify raw API / network exceptions into domain-specific LLMError types:
          - 401, 403 -> LLMAuthenticationError (Non-retryable)
          - 404 -> LLMInvalidModelError (Non-retryable)
          - 400 -> LLMClientError (Non-retryable)
          - 429 -> LLMRateLimitError (Retryable)
          - 500, 502, 503, 504 -> LLMUnavailableError (Retryable)
          - Timeout -> LLMTimeoutError (Retryable)
          - Network -> LLMNetworkError (Retryable)
        """
        if isinstance(exc, LLMError):
            return exc

        # Check for Google GenAI API errors
        from google.genai import errors as genai_errors

        if isinstance(exc, genai_errors.APIError):
            code = getattr(exc, "code", None)
            status = str(getattr(exc, "status", "") or "").upper()
            raw_msg = getattr(exc, "message", str(exc)) or str(exc)
            msg = self._sanitize(raw_msg)

            # 404: Invalid model ID or model unavailable for this tier/API version
            if code == 404 or status == "NOT_FOUND":
                return LLMInvalidModelError(
                    f"Gemini model '{self._model_name}' is not found or unavailable (HTTP 404). "
                    "Verify AI_MODEL and the configured account's model access. "
                    f"Details: {msg}"
                )

            # 401 / 403: Authentication or permission errors
            if (
                code in (401, 403)
                or status in ("PERMISSION_DENIED", "UNAUTHENTICATED")
            ):
                return LLMAuthenticationError(
                    f"Gemini API authentication failed (HTTP {code}, status '{status}'). "
                    f"Verify that AI_API_KEY is valid and has Gemini API permissions. "
                    f"Details: {msg}"
                )

            # 429: Rate limit or quota exhausted
            if (
                code == 429
                or status == "RESOURCE_EXHAUSTED"
            ):
                return LLMRateLimitError(
                    f"Gemini API rate limit or quota exceeded (HTTP 429, status '{status}'). "
                    f"Details: {msg}"
                )

            # 5xx: Server unavailable, internal, or overloaded
            if (
                code in (500, 502, 503, 504)
                or status in ("UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED")
            ):
                return LLMUnavailableError(
                    f"Gemini service or model is temporarily unavailable (HTTP {code}, status '{status}'). "
                    f"Details: {msg}"
                )

            # General 4xx client errors (e.g. 400 Bad Request)
            if code and 400 <= code < 500:
                return LLMClientError(
                    f"Gemini client request error (HTTP {code}, status '{status}'). "
                    f"Details: {msg}"
                )

            # Other status codes
            return LLMUnavailableError(
                f"Gemini API server error (HTTP {code}, status '{status}'): {msg}"
            )

        if isinstance(exc, asyncio.TimeoutError):
            return LLMTimeoutError(f"Gemini API request timed out: {self._sanitize(str(exc))}")

        if isinstance(exc, (httpx.TransportError, httpx.NetworkError, ConnectionError, OSError)):
            return LLMNetworkError(
                f"Network error connecting to Gemini API: {self._sanitize(str(exc))}"
            )

        return LLMUnavailableError(
            f"Unexpected error communicating with Gemini API: {self._sanitize(str(exc))}"
        )

    async def generate_structured(
        self,
        schema: Type[T],
        messages: list[dict[str, str]],
        opts: Optional[GenerateOpts] = None,
    ) -> T:
        opts = opts or GenerateOpts()

        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.insert(0, f"[System Instruction]\n{content}")
            else:
                parts.append(f"[{role.capitalize()}]\n{content}")

        combined_prompt = "\n\n".join(parts)

        config = self._types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=opts.max_tokens,
            temperature=opts.temperature,
        )

        @retry(
            retry=retry_if_exception_type(RETRYABLE_LLM_ERRORS),
            stop=stop_after_attempt(_MAX_RETRIES),
            wait=wait_exponential(min=_RETRY_MIN_WAIT, max=_RETRY_MAX_WAIT, multiplier=2),
            before_sleep=_log_retry_attempt,
            reraise=True,
        )
        async def _call_with_retry() -> T:
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model_name,
                        contents=combined_prompt,
                        config=config,
                    ),
                    timeout=opts.timeout_seconds,
                )
            except Exception as raw_exc:
                classified = self._classify_error(raw_exc)
                raise classified from raw_exc

            raw_text = getattr(response, "text", "") or ""
            logger.debug("[GeminiProvider] Response received (%d chars)", len(raw_text))

            try:
                return schema.model_validate_json(raw_text)
            except (ValidationError, json.JSONDecodeError) as schema_exc:
                raise LLMSchemaError(
                    f"Gemini response does not match schema '{schema.__name__}'."
                ) from schema_exc

        return await _call_with_retry()

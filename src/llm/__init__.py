"""
LLM Provider protocol and shared types.

All pipeline code calls `LLMProvider.generate_structured()` — it never
imports provider-specific SDKs directly. This keeps providers swappable
via the AI_PROVIDER environment variable.
"""
import asyncio
from typing import Any, Optional, Protocol, Type, TypeVar, runtime_checkable
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class GenerateOpts(BaseModel):
    """Options passed to every LLM call."""
    max_tokens: int = 1024
    temperature: float = 0.3
    timeout_seconds: float = 30.0


@runtime_checkable
class LLMProvider(Protocol):
    """
    Minimal interface every provider must implement.

    generate_structured() calls the LLM and parses the response into
    the given Pydantic schema. It never returns raw text or dicts.
    """

    async def generate_structured(
        self,
        schema: Type[T],
        messages: list[dict[str, str]],
        opts: Optional[GenerateOpts] = None,
    ) -> T:
        """
        Call the LLM with `messages` and return a validated instance of `schema`.

        Args:
            schema:   Pydantic model class — the LLM must return JSON matching it.
            messages: List of {role, content} dicts (OpenAI-style message format).
            opts:     Optional call-level overrides for tokens, temperature, timeout.

        Raises:
            LLMSchemaError:  LLM returned JSON that does not match `schema` after retry.
            LLMTimeoutError: Call exceeded opts.timeout_seconds.
            LLMBudgetError:  Request would exceed token budget.
        """
        ...


# ── Provider-level errors ─────────────────────────────────────────────────────

class LLMError(Exception):
    """Base class for all LLM provider errors."""


class LLMAuthenticationError(LLMError):
    """Raised when API key is missing, invalid, or permissions are denied (HTTP 401/403)."""


class LLMInvalidModelError(LLMError):
    """Raised when the requested model ID is invalid, deprecated, or not found (HTTP 404)."""


class LLMClientError(LLMError):
    """Raised when the client request is invalid or malformed (HTTP 400)."""


class LLMRateLimitError(LLMError):
    """Raised when the API rate limit or quota has been exhausted (HTTP 429)."""


class LLMUnavailableError(LLMError):
    """Raised when the LLM service or model is temporarily unavailable (HTTP 500/502/503/504)."""


class LLMNetworkError(LLMError):
    """Raised on network connection failures or transport errors."""


class LLMSchemaError(LLMError):
    """LLM returned output that does not conform to the expected schema."""


class LLMTimeoutError(LLMError):
    """LLM call exceeded the configured timeout."""


class LLMBudgetError(LLMError):
    """Request would exceed the configured token budget."""


# Errors that are transient and safe to retry with bounded exponential backoff
RETRYABLE_LLM_ERRORS = (
    LLMUnavailableError,
    LLMRateLimitError,
    LLMNetworkError,
    LLMTimeoutError,
)

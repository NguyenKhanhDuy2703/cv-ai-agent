"""Classified stage failures and safe diagnostics; never expose prompts/provider text."""
from contextvars import ContextVar
from pathlib import Path
import traceback

from . import (
    LLMAuthenticationError, LLMBudgetError, LLMClientError, LLMInvalidModelError,
    LLMNetworkError, LLMRateLimitError, LLMSchemaError, LLMTimeoutError, LLMUnavailableError,
)

JOB_CONTEXT: ContextVar[dict[str, str]] = ContextVar("generation_log_context", default={})

_ERRORS = {
    LLMAuthenticationError: ("LLM_AUTHENTICATION_ERROR", "Gemini authentication failed; check AI_API_KEY and permissions."),
    LLMInvalidModelError: ("LLM_INVALID_MODEL", "Gemini model is unavailable; check AI_MODEL and model access."),
    LLMClientError: ("LLM_INVALID_REQUEST", "Gemini rejected the request; check the provider configuration and request schema."),
    LLMRateLimitError: ("LLM_RATE_LIMIT", "Gemini rate limit or quota exceeded after bounded retries."),
    LLMNetworkError: ("LLM_NETWORK_ERROR", "Gemini connection failed after bounded retries."),
    LLMTimeoutError: ("LLM_TIMEOUT", "Gemini request timed out after bounded retries."),
    LLMUnavailableError: ("LLM_UNAVAILABLE", "Gemini is unavailable after bounded retries."),
    LLMSchemaError: ("LLM_SCHEMA_ERROR", "Gemini output did not match the required structured schema."),
    LLMBudgetError: ("LLM_BUDGET_ERROR", "The model request exceeded its configured budget."),
}


class GenerationStepError(Exception):
    def __init__(self, stage: str, cause: Exception, schema: str, source_id: str = ""):
        self.stage = stage
        self.schema = schema
        self.error_type = type(cause).__name__
        self.source_id = source_id
        self.code, message = next((value for kind, value in _ERRORS.items() if isinstance(cause, kind)),
                                  ("GENERATION_FAILED", "Generation failed; inspect the worker log using jobId."))
        super().__init__(message)


def safe_error_details(error: Exception) -> dict[str, str]:
    """Only static categories and source locations, without values from exceptions."""
    details = {"code": "GENERATION_FAILED", "message": "Generation failed; inspect the worker log using jobId.",
               "stage": "generation", "errorType": type(error).__name__}
    if isinstance(error, GenerationStepError):
        details.update(code=error.code, message=str(error), stage=error.stage,
                       errorType=error.error_type, schema=error.schema)
        if error.source_id:
            details["sourceId"] = error.source_id
    cause = error.__cause__ or error
    trace = (cause.__traceback__ if cause else None) or error.__traceback__
    frames = traceback.extract_tb(trace) if trace else []
    # Only our code's frame/function/line; no source text, locals or raw traceback.
    own_frames = [frame for frame in frames if "src" in Path(frame.filename).parts]
    if own_frames:
        frame = own_frames[-1]
        parts = Path(frame.filename).parts
        relative = "/".join(parts[parts.index("src"):])
        details["location"] = f"{relative}:{frame.lineno}:{frame.name}"
    return details


async def generate_at_stage(provider, schema, messages, stage: str, source_id: str = ""):
    try:
        return await provider.generate_structured(schema, messages)
    except Exception as error:
        raise GenerationStepError(stage, error, schema.__name__, source_id) from error


def require_provider(provider):
    if provider is None:
        raise ValueError("An explicit LLM provider is required; there is no offline generation mode")
    return provider

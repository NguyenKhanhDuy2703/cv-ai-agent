"""
Factory to instantiate the configured LLMProvider based on settings.
"""
from ..config import settings
from . import LLMProvider


def get_llm_provider() -> LLMProvider:
    """
    Returns an LLMProvider instance corresponding to `settings.ai_provider`.
    """
    settings.validate_generation_runtime()
    provider_name = settings.ai_provider.lower()

    if provider_name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
        )
    else:
        raise ValueError(f"Unsupported AI_PROVIDER: '{settings.ai_provider}'")

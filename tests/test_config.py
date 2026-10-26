"""
Tests for config validation.
These tests must run BEFORE the module-level `settings` singleton is imported,
so we use monkeypatch + importlib.reload to test fresh Settings instances.
"""
import os
import pytest
from pydantic import ValidationError


def make_settings(env_overrides: dict):
    """Helper: create a fresh Settings with the given env vars."""
    import importlib
    import src.config as cfg_module

    old_env = {}
    # Clear relevant keys
    for k in [
        "AI_PORT",
        "AI_MAX_BODY_SIZE",
        "FRONTEND_ORIGIN",
        "AI_PROVIDER",
        "AI_API_KEY",
        "AI_API_URL",
        "AI_MODEL",
    ]:
        old_env[k] = os.environ.pop(k, None)

    os.environ.update({k: str(v) for k, v in env_overrides.items()})
    try:
        importlib.reload(cfg_module)
        return cfg_module.Settings()
    finally:
        # Restore env
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        importlib.reload(cfg_module)


class TestEnvValidation:
    def test_provider_mock_no_key_required(self):
        """provider=mock (stub/mock) should start fine without API key."""
        s = make_settings({"AI_PROVIDER": "mock"})
        assert s.ai_provider == "mock"

    def test_provider_gemini_with_key_ok(self):
        """provider=gemini with key + model should be valid."""
        s = make_settings({
            "AI_PROVIDER": "gemini",
            "AI_API_KEY": "test-key-abc",
            "AI_MODEL": "gemini-2.0-flash",
        })
        assert s.ai_provider == "gemini"
        assert s.ai_api_key == "test-key-abc"

    def test_provider_gemini_missing_key_raises(self):
        """provider=gemini without API key must raise ConfigurationError (wrapped in ValidationError)."""
        with pytest.raises(ValidationError) as exc_info:
            make_settings({"AI_PROVIDER": "gemini", "AI_API_KEY": "", "AI_MODEL": "gemini-2.0-flash"})
        assert "AI_API_KEY" in str(exc_info.value)

    def test_provider_gemini_missing_model_raises(self):
        """provider=gemini without model must raise ConfigurationError (wrapped in ValidationError)."""
        with pytest.raises(ValidationError) as exc_info:
            make_settings({"AI_PROVIDER": "gemini", "AI_API_KEY": "some-key", "AI_MODEL": ""})
        assert "AI_MODEL" in str(exc_info.value)

    def test_provider_openai_is_unsupported_raises(self):
        """provider=openai is dropped from provider list until implemented."""
        with pytest.raises((ValidationError, ValueError)):
            make_settings({"AI_PROVIDER": "openai", "AI_API_KEY": "dummy", "AI_MODEL": "gpt-4o"})

    def test_invalid_provider_raises(self):
        """Unknown provider value must raise ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            make_settings({"AI_PROVIDER": "unknown_provider"})

    def test_default_port_is_8001(self):
        """Default port should be 8001 when not set."""
        s = make_settings({"AI_PROVIDER": "mock"})
        assert s.ai_port == 8001

    def test_default_max_body_size_is_10_mib(self):
        """Request body limit defaults to 10 MiB when not configured."""
        s = make_settings({"AI_PROVIDER": "mock"})
        assert s.ai_max_body_size == 10 * 1024 * 1024

    def test_max_body_size_can_be_overridden(self):
        """Request body limit can be configured in bytes through the environment."""
        s = make_settings({"AI_PROVIDER": "mock", "AI_MAX_BODY_SIZE": 5 * 1024 * 1024})
        assert s.ai_max_body_size == 5 * 1024 * 1024

    def test_max_body_size_must_be_positive(self):
        """A zero or negative request body limit is invalid configuration."""
        with pytest.raises(ValidationError):
            make_settings({"AI_PROVIDER": "mock", "AI_MAX_BODY_SIZE": 0})


"""Runtime selection, worker credentials and independent API/CLI configuration."""
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import ConfigurationError, Settings


def make_settings(overrides=None):
    with patch.dict(os.environ, {}, clear=True):
        return Settings(_env_file=None, **(overrides or {}))


class TestEnvValidation:
    def test_runtime_defaults_to_gemini_without_import_time_credentials(self):
        config = make_settings()
        assert config.ai_provider == "gemini"
        assert config.ai_database_url == ""
        assert config.ai_port == 8001
        assert config.ai_max_body_size == 10 * 1024 * 1024
        assert config.ai_job_timeout_seconds == 120
        assert config.ai_worker_concurrency == 2
        assert config.ai_job_max_attempts == 2
        assert config.ai_retention_hours == 24

    def test_worker_requires_credentials(self):
        with pytest.raises(ConfigurationError, match="AI_API_KEY"):
            make_settings().validate_generation_runtime()
        with pytest.raises(ConfigurationError, match="AI_MODEL"):
            make_settings({"AI_API_KEY": "test-key"}).validate_generation_runtime()
        make_settings({"AI_API_KEY": "test-key", "AI_MODEL": "test-model"}).validate_generation_runtime()

    @pytest.mark.parametrize("provider", ["mock", "core", "openai", "unknown_provider"])
    def test_non_runtime_providers_are_rejected(self, provider):
        with pytest.raises(ValidationError):
            make_settings({"AI_PROVIDER": provider})

    @pytest.mark.parametrize("name,value", [
        ("AI_WORKER_CONCURRENCY", 0), ("AI_MAX_BODY_SIZE", 0),
        ("AI_LEASE_SECONDS", 5), ("AI_RETENTION_HOURS", 0),
    ])
    def test_invalid_runtime_limits_are_rejected(self, name, value):
        with pytest.raises(ValidationError):
            make_settings({name: value})

    def test_max_body_size_can_be_overridden(self):
        assert make_settings({"AI_MAX_BODY_SIZE": 5 * 1024 * 1024}).ai_max_body_size == 5 * 1024 * 1024

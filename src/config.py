from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Providers that require an API key and model name
_LIVE_PROVIDERS = {"gemini"}


class ConfigurationError(ValueError):
    """Raised at startup when required environment variables are missing."""


class Settings(BaseSettings):
    ai_port: int = Field(default=8001, alias="AI_PORT")
    ai_max_body_size: int = Field(
        default=10 * 1024 * 1024,
        alias="AI_MAX_BODY_SIZE",
        gt=0,
        description="Maximum accepted HTTP request body size in bytes",
    )
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")
    ai_provider: Literal["mock", "gemini"] = Field(default="mock", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_api_url: str = Field(default="", alias="AI_API_URL")
    ai_model: str = Field(default="", alias="AI_MODEL")
    ai_secret_key: str = Field(default="", alias="AI_SECRET_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_live_provider_fields(self) -> "Settings":
        if self.ai_provider in _LIVE_PROVIDERS:
            if not self.ai_api_key:
                raise ConfigurationError(
                    f"AI_API_KEY is required when AI_PROVIDER='{self.ai_provider}'. "
                    "Set it in your .env file."
                )
            if not self.ai_model:
                raise ConfigurationError(
                    f"AI_MODEL is required when AI_PROVIDER='{self.ai_provider}'. "
                    "Example: AI_MODEL=gemini-2.0-flash"
                )
        return self


settings = Settings()

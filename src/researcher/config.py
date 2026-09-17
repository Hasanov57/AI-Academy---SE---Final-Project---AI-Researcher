"""Typed application settings loaded from environment variables and ``.env``."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings shared by all application layers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    llm_provider: Literal["openai", "anthropic", "gemini"] = "gemini"
    llm_model: str = "gemini-2.5-flash"
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None

    web_search_provider: Literal["tavily", "serper", "duckduckgo"] = "tavily"
    tavily_api_key: SecretStr | None = None
    serper_api_key: SecretStr | None = None

    database_url: SecretStr = SecretStr("postgresql://researcher@localhost:5432/researcher")
    storage_backend: Literal["postgres", "memory"] = "postgres"

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cache_ttl_seconds: int = Field(default=86_400, ge=0, le=2_592_000)
    per_source_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    synthesis_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    max_sources_per_query: int = Field(default=3, ge=1, le=10)
    max_parallel_sources: int = Field(default=3, ge=1, le=10)
    max_retry_attempts: int = Field(default=3, ge=1, le=8)
    retry_min_wait_seconds: float = Field(default=0.25, ge=0, le=30)
    retry_max_wait_seconds: float = Field(default=4.0, ge=0, le=120)
    arxiv_min_interval_seconds: float = Field(default=1.0, ge=0, le=30)
    question_max_length: int = Field(default=1000, ge=50, le=10_000)
    http_user_agent: str = (
        "AsyncResearchAssistant/1.0 (AI-ENG-110; contact: your-email@example.com)"
    )

    @field_validator("llm_model")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        """Reject an empty model identifier early."""
        value = value.strip()
        if not value:
            raise ValueError("LLM_MODEL must not be empty")
        return value

    @field_validator("http_user_agent")
    @classmethod
    def validate_http_user_agent(cls, value: str) -> str:
        """Require an identifiable user agent for public research APIs."""
        value = value.strip()
        if not value:
            raise ValueError("HTTP_USER_AGENT must not be empty")
        return value

    @model_validator(mode="after")
    def validate_wait_range(self) -> Settings:
        """Ensure exponential-backoff bounds are ordered."""
        if self.retry_min_wait_seconds > self.retry_max_wait_seconds:
            raise ValueError("RETRY_MIN_WAIT_SECONDS cannot exceed RETRY_MAX_WAIT_SECONDS")
        return self

    def validate_live_credentials(self) -> None:
        """Validate only the credentials needed for a live request."""
        llm_keys = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "gemini": self.google_api_key,
        }
        if llm_keys[self.llm_provider] is None:
            raise ValueError(f"Missing API key for LLM_PROVIDER={self.llm_provider}")
        web_keys = {
            "tavily": self.tavily_api_key,
            "serper": self.serper_api_key,
            "duckduckgo": SecretStr("not-required"),
        }
        if web_keys[self.web_search_provider] is None:
            raise ValueError(f"Missing API key for WEB_SEARCH_PROVIDER={self.web_search_provider}")
        if "your-email@example.com" in self.http_user_agent.casefold():
            raise ValueError(
                "HTTP_USER_AGENT must contain your real contact email for Wikipedia requests"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one settings object per process."""
    return Settings()

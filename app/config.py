from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using pydantic-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./tjdft.db",
        description="Database connection URL",
    )

    # OpenAI (optional)
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for AI features",
    )

    # Redis/Cache
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for caching",
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache time-to-live in seconds",
    )

    # Application
    app_name: str = Field(
        default="TJDFT API",
        description="Application name",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode",
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    This function caches the settings to avoid re-reading the .env file.
    """
    return Settings()

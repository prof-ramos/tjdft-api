import os
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
        default_factory=lambda: _default_database_url(),
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

    # MCP
    mcp_character_limit: int = Field(
        default=25000,
        ge=1000,
        description="Maximum size (in characters) for MCP tool responses",
    )
    mcp_enable_ai_tools: bool = Field(
        default=False,
        description="Enable optional AI MCP tools",
    )
    mcp_request_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Timeout used by MCP tools for upstream requests",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    This function caches the settings to avoid re-reading the .env file.
    """
    return Settings()


def _default_database_url() -> str:
    """Return a writable SQLite path for the current runtime."""
    if os.getenv("VERCEL"):
        return "sqlite+aiosqlite:////tmp/tjdft.db"
    return "sqlite+aiosqlite:///./tjdft.db"

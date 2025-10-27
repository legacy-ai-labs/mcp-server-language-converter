"""Application configuration using Pydantic settings."""

import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[misc]
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mcp_server"
    database_echo: bool = False

    # Application
    app_name: str = "MCP Server Blueprint"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Logging
    log_level: str = "INFO"

    # HTTP Streaming
    http_host: str = "0.0.0.0"  # nosec B104 - Development default, configurable via env
    http_port: int = 8000
    http_streaming_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def _log_config_error(msg: str) -> None:
    """Log configuration error to stderr."""
    print(f"CONFIG ERROR: {msg}", file=sys.stderr)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

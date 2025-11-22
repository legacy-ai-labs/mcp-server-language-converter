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
    app_name: str = "MCP Server Language Converter"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Logging
    log_level: str = "INFO"

    # HTTP Streaming
    http_host: str = "0.0.0.0"  # nosec B104 - Development default, configurable via env
    http_port: int = 8000
    http_streaming_enabled: bool = True

    # Streamable HTTP (recommended for web deployments)
    streamable_http_host: str = "0.0.0.0"  # nosec B104 - Development default, configurable via env
    streamable_http_port: int = 8002
    streamable_http_enabled: bool = True

    # Observability & Metrics
    enable_metrics: bool = True  # Enable Prometheus metrics collection
    enable_execution_logging: bool = True  # Enable database logging of executions
    metrics_retention_days: int = 30  # How long to keep execution records in DB
    log_tool_inputs: bool = False  # Store input parameters (may contain PII)
    log_tool_outputs: bool = False  # Store output data (may contain PII)
    max_latency_samples: int = 1000  # Maximum latency samples to keep in memory
    metrics_port: int = 9090  # Port for standalone metrics server

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

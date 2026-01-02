"""Application configuration using Pydantic settings."""

import sys
from functools import lru_cache
from importlib.metadata import version as get_package_version

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_version() -> str:
    """Get version from package metadata (pyproject.toml).

    Falls back to "0.0.0-dev" if package is not installed.
    """
    try:
        return get_package_version("mcp-server-language-converter")
    except Exception:
        return "0.0.0-dev"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mcp_server"
    database_echo: bool = False

    # Application
    app_name: str = "MCP Server Language Converter"
    app_version: str = _get_version()  # Read from pyproject.toml
    environment: str = "development"

    # Logging
    log_level: str = "INFO"

    # SSE Transport (HTTP Streaming via Server-Sent Events)
    http_host: str = "::"  # nosec B104 - Dual-stack IPv4/IPv6, configurable via env
    http_port: int = 8000  # SSE General: http://<IP>:8000/sse
    http_port_cobol: int = 8001  # SSE COBOL: http://<IP>:8001/sse
    http_streaming_enabled: bool = True

    # Streamable HTTP Transport (recommended for web deployments)
    streamable_http_host: str = "::"  # nosec B104 - Dual-stack IPv4/IPv6, configurable via env
    streamable_http_port: int = 8002  # Streamable HTTP General: http://<IP>:8002/mcp
    streamable_http_port_cobol: int = 8003  # Streamable HTTP COBOL: http://<IP>:8003/mcp
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

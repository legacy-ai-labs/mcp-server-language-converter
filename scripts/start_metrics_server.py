#!/usr/bin/env python3
"""Standalone Prometheus metrics server.

This server exposes Prometheus metrics at /metrics endpoint.
Run this alongside the MCP server to access metrics via HTTP.

Usage:
    uv run python scripts/start_metrics_server.py
    # Metrics available at http://localhost:9090/metrics
"""

import logging
import sys

import uvicorn
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from src.core.config import get_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def create_metrics_app() -> FastAPI:
    """Create FastAPI app with Prometheus metrics endpoint."""
    app = FastAPI(title="MCP Server Metrics")

    @app.get("/metrics")  # type: ignore[misc]
    async def metrics() -> Response:
        """Prometheus metrics endpoint in exposition format."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get("/health")  # type: ignore[misc]
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


def main() -> None:
    """Run the metrics server."""
    settings = get_settings()

    if not settings.enable_metrics:
        logger.warning("Metrics are disabled in configuration. Enable with ENABLE_METRICS=true")
        return

    app = create_metrics_app()

    # Default to port 9090 (standard Prometheus metrics port)
    metrics_port = 9090
    metrics_host = "0.0.0.0"  # nosec B104 - Metrics server needs to bind to all interfaces

    logger.info(f"Starting Prometheus metrics server on http://{metrics_host}:{metrics_port}")
    logger.info(f"Metrics endpoint: http://localhost:{metrics_port}/metrics")
    logger.info(f"Health check: http://localhost:{metrics_port}/health")

    try:
        uvicorn.run(app, host=metrics_host, port=metrics_port, log_level="info")
    except KeyboardInterrupt:
        logger.info("Metrics server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

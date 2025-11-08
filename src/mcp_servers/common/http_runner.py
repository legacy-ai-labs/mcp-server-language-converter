"""Generic HTTP streaming transport runner for MCP servers.

This module provides a reusable HTTP streaming server runner that can be used
by any domain-specific MCP server. It handles server initialization, tool loading,
and running the server with HTTP streaming (SSE) transport.
"""

import asyncio
import logging
import sys
import traceback
from typing import Any

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.services.prometheus_metrics_service import PROMETHEUS_METRICS
from src.mcp_servers.common.base_server import create_mcp_server
from src.mcp_servers.common.dynamic_loader import load_tools_from_database


# Configure logging to stderr so HTTP clients can see it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Important: log to stderr for HTTP streaming
)

logger = logging.getLogger(__name__)


async def startup(domain: str, server_name: str | None = None) -> Any:
    """Initialize MCP server and load tools for the specified domain.

    Args:
        domain: Domain to load tools for (e.g., "general", "kubernetes")
        server_name: Optional custom server name

    Returns:
        Initialized FastMCP server instance with tools loaded

    Raises:
        Exception: If server initialization or tool loading fails
    """
    try:
        settings = get_settings()

        # Initialize Prometheus server metadata
        if settings.enable_metrics:
            PROMETHEUS_METRICS.set_server_info(
                version=settings.app_version,
                python_version=sys.version.split()[0],
                environment=settings.environment,
            )
            logger.info("Prometheus metrics initialized")

        # Create MCP server instance
        mcp = create_mcp_server(domain=domain, server_name=server_name)

        # Load tools from database for this domain with HTTP transport
        await load_tools_from_database(mcp, domain, transport="http")
        logger.info(f"Tools loaded successfully for domain: {domain}")

        return mcp

    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise


def run_http_server(domain: str, server_name: str | None = None) -> None:
    """Run MCP server with HTTP streaming transport for the specified domain.

    This is the main entry point for domain-specific HTTP streaming servers.
    Prometheus metrics are collected but not exposed via HTTP endpoint
    (FastMCP doesn't support custom routes). Metrics can be accessed
    programmatically via the Prometheus client library.

    Args:
        domain: Domain this server handles (e.g., "general", "kubernetes")
        server_name: Optional custom server name

    Example:
        >>> run_http_server(domain="general")
        >>> run_http_server(domain="kubernetes", server_name="K8s MCP Server")
    """
    try:
        # Log startup to stderr for HTTP streaming clients
        print(f"HTTP Streaming MCP Server starting for domain: {domain}...", file=sys.stderr)
        logger.info(f"Running MCP server with HTTP streaming for domain: {domain}")

        # Initialize server and load tools
        mcp = asyncio.run(startup(domain=domain, server_name=server_name))

        # Run MCP server with HTTP streaming transport (SSE)
        # Tools are now loaded dynamically from database
        settings = get_settings()

        # Configure CORS middleware to allow browser connections
        # This is essential for SSE connections from web browsers
        cors_middleware = Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for development
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

        logger.info("CORS enabled for SSE transport - browser connections allowed")

        # Note: FastMCP doesn't support custom routes via app parameter
        # Metrics are still collected and tracked in memory via Prometheus client
        # To expose metrics via HTTP, run a separate metrics server or use
        # a monitoring agent that can scrape from Prometheus client's registry
        logger.info(
            "Prometheus metrics are collected but not exposed via HTTP endpoint. "
            "Use a Prometheus client library to access metrics programmatically."
        )

        mcp.run(
            transport="sse",
            host=settings.http_host,
            port=settings.http_port,
            middleware=[cors_middleware],  # Pass CORS middleware to SSE transport
        )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        print("HTTP Streaming MCP Server shutting down (KeyboardInterrupt)", file=sys.stderr)
    except Exception as e:
        # Log to stderr so HTTP clients can see the error
        error_msg = f"Server error: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

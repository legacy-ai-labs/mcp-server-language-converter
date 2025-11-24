"""Generic Streamable HTTP transport runner for MCP servers.

This module provides a reusable Streamable HTTP server runner that can be used
by any domain-specific MCP server. It handles server initialization, tool loading,
and running the server with Streamable HTTP transport (recommended for web deployments).
"""

__all__ = ["run_streamable_http_server"]

import asyncio
import importlib
import logging
import sys
import traceback
from typing import Any

from src.core.config import get_settings
from src.core.services.common.prometheus_metrics_service import PROMETHEUS_METRICS
from src.mcp_servers.common.base_server import create_mcp_server
from src.mcp_servers.common.tool_registry import load_tools_from_registry


# Configure logging to stderr so HTTP clients can see it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Important: log to stderr for HTTP streaming
)

logger = logging.getLogger(__name__)

settings = get_settings()


def _import_domain_tools(domain: str) -> None:
    """Import domain tools module to trigger decorator registration.

    Args:
        domain: Domain to import tools for

    Raises:
        ImportError: If domain tools module cannot be imported
    """
    try:
        if domain == "general":
            importlib.import_module("src.mcp_servers.mcp_general.tools")
        elif domain == "cobol_analysis":
            importlib.import_module("src.mcp_servers.mcp_cobol_analysis.tools")
        # Add more domains as they migrate
        logger.info(f"Imported tools module for domain: {domain}")
    except ImportError as e:
        logger.warning(f"Could not import tools for domain '{domain}': {e}")


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
        # Initialize Prometheus server metadata
        if settings.enable_metrics:
            PROMETHEUS_METRICS.set_server_info(
                version=settings.app_version,
                python_version=sys.version.split()[0],
                environment=settings.environment,
            )
            logger.info("Prometheus metrics initialized")

        # Create MCP server instance with Streamable HTTP transport
        mcp = create_mcp_server(domain=domain, server_name=server_name, transport="streamable-http")

        # Import domain tools module to trigger decorator registration
        logger.info(f"Loading tools for domain: {domain}")
        _import_domain_tools(domain)

        # Load tools from registry
        await load_tools_from_registry(mcp, domain, transport="streamable-http")

        logger.info(f"Tools loaded successfully for domain: {domain}")

        return mcp

    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise


def run_streamable_http_server(domain: str, server_name: str | None = None) -> None:
    """Run MCP server with Streamable HTTP transport for the specified domain.

    This is the main entry point for domain-specific Streamable HTTP servers.
    Streamable HTTP is the recommended transport for web-based deployments and microservices.
    Tools are loaded from the decorator-based registry.

    Args:
        domain: Domain this server handles (e.g., "general", "kubernetes")
        server_name: Optional custom server name

    Example:
        >>> run_streamable_http_server(domain="general")
        >>> run_streamable_http_server(domain="kubernetes", server_name="K8s MCP Server")
    """
    try:
        # Log startup to stderr for HTTP streaming clients
        print(f"Streamable HTTP MCP Server starting for domain: {domain}...", file=sys.stderr)
        logger.info(f"Running MCP server with Streamable HTTP for domain: {domain}")

        # Initialize server and load tools
        mcp = asyncio.run(startup(domain=domain, server_name=server_name))

        # Run MCP server with Streamable HTTP transport
        mcp.run(
            transport="streamable-http",
            host=settings.streamable_http_host,
            port=settings.streamable_http_port,
        )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        print("Streamable HTTP MCP Server shutting down (KeyboardInterrupt)", file=sys.stderr)
    except Exception as e:
        # Log to stderr so HTTP clients can see the error
        error_msg = f"Server error: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

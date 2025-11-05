"""Generic Streamable HTTP transport runner for MCP servers.

This module provides a reusable Streamable HTTP server runner that can be used
by any domain-specific MCP server. It handles server initialization, tool loading,
and running the server with Streamable HTTP transport (recommended for web deployments).
"""

__all__ = ["run_streamable_http_server"]

import asyncio
import logging
import sys
import traceback
from typing import Any

from src.core.config import get_settings
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
        # Create MCP server instance
        mcp = create_mcp_server(domain=domain, server_name=server_name)

        # Load tools from database for this domain
        await load_tools_from_database(mcp, domain)
        logger.info(f"Tools loaded successfully for domain: {domain}")

        return mcp

    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise


def run_streamable_http_server(domain: str, server_name: str | None = None) -> None:
    """Run MCP server with Streamable HTTP transport for the specified domain.

    This is the main entry point for domain-specific Streamable HTTP servers.
    Streamable HTTP is the recommended transport for web-based deployments and microservices.

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
        # Tools are now loaded dynamically from database
        settings = get_settings()

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

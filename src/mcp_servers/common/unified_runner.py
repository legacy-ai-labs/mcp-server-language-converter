"""Unified protocol-agnostic MCP server runner.

This module provides a single entry point for running MCP servers with any transport:
- stdio: Standard input/output (for Claude Desktop, Cursor IDE)
- sse: Server-Sent Events (HTTP streaming with SSE)
- streamable-http: Streamable HTTP (recommended for web deployments)

The server automatically configures itself based on the transport type.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import sys
import traceback
from typing import Any, Literal

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.services.common.prometheus_metrics_service import PROMETHEUS_METRICS
from src.mcp_servers.common.base_server import create_mcp_server
from src.mcp_servers.common.tool_registry import load_tools_from_registry


# Configure logging to stderr so clients can see it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)

settings = get_settings()

# Transport type definitions
TransportType = Literal["stdio", "sse", "streamable-http"]


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


def _get_transport_mapping(transport: TransportType) -> tuple[str, str]:
    """Map transport type to create_mcp_server and load_tools_from_registry transport values.

    Args:
        transport: Transport type ("stdio", "sse", or "streamable-http")

    Returns:
        Tuple of (server_transport, registry_transport)
        - server_transport: Transport value for create_mcp_server
        - registry_transport: Transport value for load_tools_from_registry

    Note:
        SSE uses "sse" for server creation but "http" for tool registry.
    """
    mapping = {
        "stdio": ("stdio", "stdio"),
        "sse": ("sse", "http"),
        "streamable-http": ("streamable-http", "streamable-http"),
    }
    return mapping.get(transport, ("stdio", "stdio"))


async def startup(
    domain: str,
    transport: TransportType = "stdio",
    server_name: str | None = None,
) -> Any:
    """Initialize MCP server and load tools for the specified domain and transport.

    Args:
        domain: Domain to load tools for (e.g., "general", "cobol_analysis")
        transport: Transport protocol ("stdio", "sse", or "streamable-http")
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

        # Map transport to correct values for server and registry
        server_transport, registry_transport = _get_transport_mapping(transport)

        # Create MCP server instance with specified transport
        mcp = create_mcp_server(
            domain=domain,
            server_name=server_name,
            transport=server_transport,
        )

        # Import domain tools module to trigger decorator registration
        logger.info(f"Loading tools for domain: {domain}")
        _import_domain_tools(domain)

        # Load tools from registry with correct transport mapping
        await load_tools_from_registry(mcp, domain, transport=registry_transport)

        logger.info(f"Tools loaded successfully for domain: {domain} (transport: {transport})")

        return mcp

    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise


def _get_transport_config(transport: TransportType) -> dict[str, Any]:
    """Get transport-specific configuration (host, port, middleware).

    Args:
        transport: Transport type

    Returns:
        Dictionary with transport configuration:
        - host: Server host
        - port: Server port
        - middleware: List of middleware (if any)
    """
    config: dict[str, Any] = {}

    if transport == "stdio":
        # STDIO doesn't need host/port
        config = {}
    elif transport == "sse":
        config = {
            "host": settings.http_host,
            "port": settings.http_port,
            "middleware": [
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],  # Allow all origins for development
                    allow_credentials=True,
                    allow_methods=["GET", "POST", "OPTIONS"],
                    allow_headers=["*"],
                ),
            ],
        }
        logger.info("CORS enabled for SSE transport - browser connections allowed")
    elif transport == "streamable-http":
        config = {
            "host": settings.streamable_http_host,
            "port": settings.streamable_http_port,
        }

    return config


def run_server(
    domain: str,
    transport: TransportType = "stdio",
    server_name: str | None = None,
) -> None:
    """Run MCP server with the specified transport protocol.

    This is a unified entry point that supports all three MCP transport protocols:
    - stdio: Standard input/output (for Claude Desktop, Cursor IDE)
    - sse: Server-Sent Events (HTTP streaming with SSE)
    - streamable-http: Streamable HTTP (recommended for web deployments)

    Args:
        domain: Domain this server handles (e.g., "general", "cobol_analysis")
        transport: Transport protocol to use ("stdio", "sse", or "streamable-http")
        server_name: Optional custom server name

    Example:
        >>> # Run with STDIO (default)
        >>> run_server(domain="general")
        >>> # Run with SSE
        >>> run_server(domain="general", transport="sse")
        >>> # Run with Streamable HTTP
        >>> run_server(domain="cobol_analysis", transport="streamable-http")
    """
    try:
        # Log startup
        transport_display = {
            "stdio": "STDIO",
            "sse": "HTTP Streaming (SSE)",
            "streamable-http": "Streamable HTTP",
        }.get(transport, transport.upper())

        print(
            f"MCP Server starting for domain: {domain} (transport: {transport_display})...",
            file=sys.stderr,
        )
        logger.info(f"Running MCP server with {transport_display} transport for domain: {domain}")

        # Initialize server and load tools
        mcp = asyncio.run(startup(domain=domain, transport=transport, server_name=server_name))

        # Get transport-specific configuration
        transport_config = _get_transport_config(transport)

        # Run MCP server with specified transport
        run_kwargs = {"transport": transport, **transport_config}
        mcp.run(**run_kwargs)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        print("MCP Server shutting down (KeyboardInterrupt)", file=sys.stderr)
    except Exception as e:
        # Log to stderr so clients can see the error
        error_msg = f"Server error: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


# Convenience functions for backward compatibility
def run_stdio_server(domain: str, server_name: str | None = None) -> None:
    """Run MCP server with STDIO transport (backward compatibility).

    Args:
        domain: Domain this server handles
        server_name: Optional custom server name
    """
    run_server(domain=domain, transport="stdio", server_name=server_name)


def run_http_server(domain: str, server_name: str | None = None) -> None:
    """Run MCP server with SSE transport (backward compatibility).

    Args:
        domain: Domain this server handles
        server_name: Optional custom server name
    """
    run_server(domain=domain, transport="sse", server_name=server_name)


def run_streamable_http_server(domain: str, server_name: str | None = None) -> None:
    """Run MCP server with Streamable HTTP transport (backward compatibility).

    Args:
        domain: Domain this server handles
        server_name: Optional custom server name
    """
    run_server(domain=domain, transport="streamable-http", server_name=server_name)

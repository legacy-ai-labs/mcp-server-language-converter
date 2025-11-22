"""Base MCP server initialization.

This module provides generic FastMCP server initialization that can be reused
across all domain-specific MCP servers. Includes automatic observability middleware.
"""

from fastmcp import FastMCP

from src.core.config import get_settings
from src.mcp_servers.common.observability_middleware import ObservabilityMiddleware


def create_mcp_server(
    domain: str, server_name: str | None = None, transport: str = "stdio"
) -> FastMCP:
    """Create a FastMCP server instance for a specific domain with observability.

    The server is automatically configured with observability middleware that
    provides comprehensive tracing, metrics, and audit logging for all tool
    executions.

    Args:
        domain: The domain this server handles (e.g., "general", "kubernetes")
        server_name: Optional custom server name. If not provided, uses format:
                    "MCP Server Language Converter - {Domain} Tools"
        transport: Transport protocol used (e.g., "stdio", "http", "sse")

    Returns:
        Configured FastMCP server instance with observability middleware
    """
    settings = get_settings()

    # Generate server name if not provided
    if not server_name:
        domain_display = domain.replace("_", " ").title()
        server_name = f"{settings.app_name} - {domain_display} Tools"

    # Create FastMCP server instance
    mcp = FastMCP(
        name=server_name,
        version=settings.app_version,
    )

    # Add observability middleware for automatic tracing
    # This wraps all tool executions with comprehensive observability
    observability_mw = ObservabilityMiddleware(domain=domain, transport=transport)
    mcp.add_middleware(observability_mw)

    return mcp

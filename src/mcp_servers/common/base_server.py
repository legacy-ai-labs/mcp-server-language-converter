"""Base MCP server initialization.

This module provides generic FastMCP server initialization that can be reused
across all domain-specific MCP servers.
"""

from fastmcp import FastMCP

from src.core.config import get_settings


def create_mcp_server(domain: str, server_name: str | None = None) -> FastMCP:
    """Create a FastMCP server instance for a specific domain.

    Args:
        domain: The domain this server handles (e.g., "general", "kubernetes")
        server_name: Optional custom server name. If not provided, uses format:
                    "MCP Server Language Converter - {Domain} Tools"

    Returns:
        Configured FastMCP server instance
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

    return mcp

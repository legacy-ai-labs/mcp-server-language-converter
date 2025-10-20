"""MCP Server setup and configuration."""

import logging

from fastmcp import FastMCP

from src.core.config import get_settings


settings = get_settings()

# Get logger (logging configured in __main__.py)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
# Note: Database integration will be added in a future phase
# Currently tools are statically registered via @mcp.tool() decorators
mcp = FastMCP(
    name=settings.app_name,
    version=settings.app_version,
)

logger.info(f"MCP Server '{settings.app_name}' v{settings.app_version} initialized")

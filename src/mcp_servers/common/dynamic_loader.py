"""Dynamic tool loading from database.

This module provides generic tool loading functionality that works across all
domain-specific MCP servers. Tools are loaded from the database and registered
with FastMCP at server startup.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from src.core.database import async_session_factory
from src.core.repositories.tool_repository import ToolRepository
from src.core.services.tool_handlers import TOOL_HANDLERS


logger = logging.getLogger(__name__)


async def load_tools_from_database(mcp: FastMCP, domain: str) -> None:
    """Load active tools for a specific domain from database and register with FastMCP.

    Args:
        mcp: FastMCP server instance to register tools with
        domain: Domain to filter tools by (e.g., "general", "kubernetes")

    Raises:
        Exception: If tool loading fails
    """
    try:
        async with async_session_factory() as session:
            tool_repo = ToolRepository(session)

            # Get active tools for this domain
            active_tools = await tool_repo.get_by_domain(domain)

            logger.info(f"Loading {len(active_tools)} tools for domain '{domain}'...")

            for tool in active_tools:
                try:
                    await register_tool_from_db(mcp, tool)
                    logger.info(f"Registered tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to register tool {tool.name}: {e}")

    except Exception as e:
        logger.error(f"Failed to load tools from database: {e}")
        raise


async def register_tool_from_db(mcp: FastMCP, tool: Any) -> None:
    """Register a single tool from database record.

    This creates tool-specific wrappers with proper signatures instead of
    using **kwargs which FastMCP doesn't support.

    Args:
        mcp: FastMCP server instance
        tool: Tool database record with name, description, and handler_name

    Raises:
        ValueError: If handler function not found in registry
    """
    # Get the handler function from registry
    handler_func = TOOL_HANDLERS.get(tool.handler_name)
    if not handler_func:
        raise ValueError(f"Handler {tool.handler_name} not found for tool {tool.name}")

    # Create specific tool wrappers based on tool name
    if tool.name == "echo":

        async def echo_tool(text: str) -> dict[str, Any]:
            """Echo back the provided text."""
            try:
                result = handler_func({"text": text})
                return result
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {e}")
                return {"success": False, "error": str(e)}

        decorated_tool = mcp.tool(name=tool.name, description=tool.description)(echo_tool)

    elif tool.name == "calculator_add":

        async def calculator_add_tool(a: float, b: float) -> dict[str, Any]:
            """Add two numbers together."""
            try:
                result = handler_func({"a": a, "b": b})
                return result
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {e}")
                return {"success": False, "error": str(e)}

        decorated_tool = mcp.tool(name=tool.name, description=tool.description)(calculator_add_tool)

    else:
        # Generic fallback for unknown tools
        async def generic_tool_wrapper(text: str = "") -> dict[str, Any]:
            """Generic wrapper for unknown tools."""
            try:
                result = handler_func({"text": text})
                return result
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {e}")
                return {"success": False, "error": str(e)}

        decorated_tool = mcp.tool(name=tool.name, description=tool.description)(
            generic_tool_wrapper
        )

    # Store reference to prevent garbage collection
    if not hasattr(mcp, "_dynamic_tools"):
        mcp._dynamic_tools = []
    mcp._dynamic_tools.append(decorated_tool)

"""Dynamic tool loading from database."""

import logging
from typing import Any

from src.core.repositories.tool_repository import ToolRepository
from src.core.services.tool_handlers import TOOL_HANDLERS
from src.mcp_servers.general.server import mcp


logger = logging.getLogger(__name__)


async def load_tools_from_database() -> None:
    """Load active tools from database and register them with FastMCP."""
    try:
        from src.core.database import async_session_factory

        async with async_session_factory() as session:
            tool_repo = ToolRepository(session)
            active_tools = await tool_repo.list_active()

            logger.info(f"Loading {len(active_tools)} tools from database...")

            for tool in active_tools:
                try:
                    await register_tool_from_db(tool)
                    logger.info(f"Registered tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to register tool {tool.name}: {e}")

    except Exception as e:
        logger.error(f"Failed to load tools from database: {e}")
        raise


async def register_tool_from_db(tool: Any) -> None:
    """Register a single tool from database record."""

    # Get the handler function
    handler_func = TOOL_HANDLERS.get(tool.handler_name)
    if not handler_func:
        logger.error(f"Handler {tool.handler_name} not found for tool {tool.name}")
        return

    # Create a specific tool function based on the tool name
    if tool.name == "echo":

        async def echo_tool(text: str) -> dict[str, Any]:
            """Echo back the provided text."""
            try:
                result = handler_func({"text": text})
                return result
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {e}")
                return {"success": False, "error": str(e)}

        # Apply the decorator
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

        # Apply the decorator
        decorated_tool = mcp.tool(name=tool.name, description=tool.description)(calculator_add_tool)

    else:
        logger.error(f"Unknown tool: {tool.name}")
        return

    # Store the tool reference to prevent garbage collection
    if not hasattr(mcp, "_dynamic_tools"):
        mcp._dynamic_tools = []
    mcp._dynamic_tools.append(decorated_tool)


async def get_tools_by_domain(domain: str) -> list[Any]:
    """Get tools for specific domain."""
    from src.core.database import async_session_factory

    async with async_session_factory() as session:
        tool_repo = ToolRepository(session)
        return await tool_repo.get_by_domain(domain)

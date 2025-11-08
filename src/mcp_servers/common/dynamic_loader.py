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
from src.core.services.observability_service import trace_tool_execution
from src.core.services.tool_handlers_service import TOOL_HANDLERS


logger = logging.getLogger(__name__)


async def load_tools_from_database(mcp: FastMCP, domain: str, transport: str = "stdio") -> None:
    """Load active tools for a specific domain from database and register with FastMCP.

    Args:
        mcp: FastMCP server instance to register tools with
        domain: Domain to filter tools by (e.g., "general", "kubernetes")
        transport: Transport protocol being used (stdio, http, rest)

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
                    await register_tool_from_db(mcp, tool, domain, transport)
                    logger.info(f"Registered tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to register tool {tool.name}: {e}")

    except Exception as e:
        logger.error(f"Failed to load tools from database: {e}")
        raise


async def register_tool_from_db(mcp: FastMCP, tool: Any, domain: str, transport: str) -> None:
    """Register a single tool from database record with observability tracing.

    This creates tool-specific wrappers with proper signatures instead of
    using **kwargs which FastMCP doesn't support. Each wrapper includes
    automatic tracing for observability.

    Args:
        mcp: FastMCP server instance
        tool: Tool database record with name, description, and handler_name
        domain: Domain the tool belongs to (for metrics)
        transport: Transport protocol (stdio, http, rest) for metrics

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
            async with trace_tool_execution(
                tool_name=tool.name,
                parameters={"text": text},
                domain=domain,
                transport=transport,
            ) as trace_ctx:
                try:
                    result = handler_func({"text": text})
                except Exception as e:
                    logger.error(f"Tool {tool.name} failed: {e}")
                    trace_ctx["status"] = "error"
                    trace_ctx["error_type"] = type(e).__name__
                    trace_ctx["error_message"] = str(e)
                    error_payload = {"success": False, "error": str(e)}
                    trace_ctx["output_data"] = error_payload
                    return error_payload

                trace_ctx["output_data"] = result
                return result

        decorated_tool = mcp.tool(name=tool.name, description=tool.description)(echo_tool)

    elif tool.name == "calculator_add":

        async def calculator_add_tool(a: float, b: float) -> dict[str, Any]:
            """Add two numbers together."""
            async with trace_tool_execution(
                tool_name=tool.name,
                parameters={"a": a, "b": b},
                domain=domain,
                transport=transport,
            ) as trace_ctx:
                try:
                    result = handler_func({"a": a, "b": b})
                except Exception as e:
                    logger.error(f"Tool {tool.name} failed: {e}")
                    trace_ctx["status"] = "error"
                    trace_ctx["error_type"] = type(e).__name__
                    trace_ctx["error_message"] = str(e)
                    error_payload = {"success": False, "error": str(e)}
                    trace_ctx["output_data"] = error_payload
                    return error_payload

                trace_ctx["output_data"] = result
                return result

        decorated_tool = mcp.tool(name=tool.name, description=tool.description)(calculator_add_tool)

    else:
        # Generic fallback for unknown tools
        async def generic_tool_wrapper(text: str = "") -> dict[str, Any]:
            """Generic wrapper for unknown tools."""
            async with trace_tool_execution(
                tool_name=tool.name,
                parameters={"text": text},
                domain=domain,
                transport=transport,
            ) as trace_ctx:
                try:
                    result = handler_func({"text": text})
                except Exception as e:
                    logger.error(f"Tool {tool.name} failed: {e}")
                    trace_ctx["status"] = "error"
                    trace_ctx["error_type"] = type(e).__name__
                    trace_ctx["error_message"] = str(e)
                    error_payload = {"success": False, "error": str(e)}
                    trace_ctx["output_data"] = error_payload
                    return error_payload

                trace_ctx["output_data"] = result
                return result

        decorated_tool = mcp.tool(name=tool.name, description=tool.description)(
            generic_tool_wrapper
        )

    # Store reference to prevent garbage collection
    if not hasattr(mcp, "_dynamic_tools"):
        mcp._dynamic_tools = []
    mcp._dynamic_tools.append(decorated_tool)

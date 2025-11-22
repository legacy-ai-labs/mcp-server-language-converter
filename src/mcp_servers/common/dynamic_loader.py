"""Dynamic tool loading from database.

This module provides generic tool loading functionality that works across all
domain-specific MCP servers. Tools are loaded from the database and registered
with FastMCP at server startup.
"""

import logging
import warnings
from typing import Any

from fastmcp import FastMCP

from src.core.database import async_session_factory
from src.core.repositories.tool_repository import ToolRepository
from src.core.services.cobol_analysis.tool_handlers_service import (
    TOOL_HANDLERS as COBOL_HANDLERS,
)
from src.core.services.common.observability_service import trace_tool_execution
from src.core.services.general.tool_handlers_service import (
    TOOL_HANDLERS as GENERAL_HANDLERS,
)


logger = logging.getLogger(__name__)


# Merge all tool handlers from different domains
TOOL_HANDLERS = {**GENERAL_HANDLERS, **COBOL_HANDLERS}


def _create_traced_tool(
    tool_name: str,
    domain: str,
    transport: str,
    tool_func: Any,
) -> Any:
    """Create a tool function with observability tracing.

    Args:
        tool_name: Name of the tool
        domain: Domain the tool belongs to
        transport: Transport protocol
        tool_func: Async function that calls the handler

    Returns:
        Tool function with tracing
    """

    async def traced_tool(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Tool wrapper with observability."""
        # Build parameters dict from args/kwargs for tracing
        parameters = kwargs.copy() if kwargs else {}
        if args:
            # For tools with positional args, map them appropriately
            param_names = list(tool_func.__code__.co_varnames[: tool_func.__code__.co_argcount])
            param_names = [p for p in param_names if p != "self"]
            for idx, arg in enumerate(args):
                if idx < len(param_names):
                    parameters[param_names[idx]] = arg

        async with trace_tool_execution(
            tool_name=tool_name,
            parameters=parameters,
            domain=domain,
            transport=transport,
        ) as trace_ctx:
            try:
                result = await tool_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                trace_ctx["status"] = "error"
                trace_ctx["error_type"] = type(e).__name__
                trace_ctx["error_message"] = str(e)
                return {"success": False, "error": str(e)}
            trace_ctx["output_data"] = result
            if not isinstance(result, dict):
                logger.warning(
                    f"Tool {tool_name} returned non-dict result: {type(result).__name__}"
                )
                return {
                    "success": False,
                    "error": f"Tool returned invalid type: {type(result).__name__}",
                }
            return result

    return traced_tool


def _create_generic_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create generic tool wrapper."""

    async def tool_impl(text: str = "") -> dict[str, Any]:
        result = handler_func({"text": text})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def generic_tool_wrapper(text: str = "") -> dict[str, Any]:
        """Generic wrapper for unknown tools."""
        result = await traced(text)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return generic_tool_wrapper


async def load_tools_from_database(mcp: FastMCP, domain: str, transport: str = "stdio") -> None:
    """Load active tools for a specific domain from database and register with FastMCP.

    .. deprecated::
        This function is deprecated as of the decorator-based migration (Phases 2-3).
        Use decorator-based registration with `load_tools_from_registry()` instead.
        This function will be removed in a future version.

        See `src/mcp_servers/common/tool_registry.py` for the new approach.

    Args:
        mcp: FastMCP server instance to register tools with
        domain: Domain to filter tools by (e.g., "general", "kubernetes")
        transport: Transport protocol being used (stdio, http, rest)

    Raises:
        Exception: If tool loading fails
    """
    warnings.warn(
        "load_tools_from_database() is deprecated. "
        "Use decorator-based registration with load_tools_from_registry() instead. "
        "See src/mcp_servers/common/tool_registry.py for details.",
        DeprecationWarning,
        stacklevel=2,
    )

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
    handler_func = TOOL_HANDLERS.get(tool.handler_name)
    if not handler_func:
        raise ValueError(f"Handler {tool.handler_name} not found for tool {tool.name}")

    # Note: General tools (echo, calculator_add) migrated to decorator-based registration (Phase 2)
    # Note: COBOL tools (parse_cobol, build_ast, build_cfg, build_dfg, build_pdg) migrated (Phase 3)
    # Remaining tools use generic wrapper
    tool_func = _create_generic_tool(handler_func, tool.name, domain, transport)

    decorated_tool = mcp.tool(name=tool.name, description=tool.description)(tool_func)

    if not hasattr(mcp, "_dynamic_tools"):
        mcp._dynamic_tools = []  # type: ignore[attr-defined]
    mcp._dynamic_tools.append(decorated_tool)  # type: ignore[attr-defined]

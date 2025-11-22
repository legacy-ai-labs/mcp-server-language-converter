"""Tool registry for decorator-based tool registration.

This module provides a registry pattern that allows domain-specific servers
to register tools using @mcp.tool() decorators while maintaining compatibility
with database-driven enable/disable functionality.
"""

import inspect
import logging
from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP

from src.core.database import async_session_factory
from src.core.repositories.tool_repository import ToolRepository
from src.core.services.common.observability_service import trace_tool_execution


logger = logging.getLogger(__name__)

# Global registry: domain -> list of (tool_name, tool_func, description)
TOOL_REGISTRY: dict[str, list[tuple[str, Callable[..., Any], str]]] = {}


def register_tool(domain: str, tool_name: str, description: str = "") -> Callable[..., Any]:
    """Decorator factory for registering tools in the registry.

    Usage:
        @register_tool(domain="general", tool_name="echo", description="Echo text")
        @mcp.tool()
        async def echo(text: str) -> dict[str, Any]:
            ...

    Args:
        domain: Domain this tool belongs to
        tool_name: Name of the tool (must match DB record)
        description: Tool description (optional, can come from DB)

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if domain not in TOOL_REGISTRY:
            TOOL_REGISTRY[domain] = []

        TOOL_REGISTRY[domain].append((tool_name, func, description))
        logger.debug(f"Registered tool '{tool_name}' for domain '{domain}'")
        return func

    return decorator


async def load_tools_from_registry(
    mcp: FastMCP,
    domain: str,
    transport: str = "stdio",  # noqa: ARG001
) -> None:
    """Load tools from registry and register with FastMCP, filtered by database.

    This function:
    1. Gets all registered tools for the domain from TOOL_REGISTRY
    2. Checks database to see which tools are active
    3. Registers only active tools with FastMCP
    4. Applies observability tracing to all tools

    Args:
        mcp: FastMCP server instance to register tools with
        domain: Domain to load tools for
        transport: Transport protocol being used (stdio, http, sse) - reserved for future use

    Raises:
        Exception: If tool loading fails
    """
    if domain not in TOOL_REGISTRY:
        logger.warning(f"No tools registered for domain '{domain}'")
        return

    try:
        async with async_session_factory() as session:
            tool_repo = ToolRepository(session)

            # Get active tools from database for this domain
            active_tools = await tool_repo.get_by_domain(domain)
            active_tool_names = {tool.name for tool in active_tools}

            # Get registered tools for this domain
            registered_tools = TOOL_REGISTRY.get(domain, [])

            logger.info(
                f"Loading {len(registered_tools)} registered tools for domain '{domain}' "
                f"({len(active_tool_names)} active in database)"
            )

            # Register each tool that is both registered and active in DB
            registered_count = 0
            for tool_name, tool_func, _description in registered_tools:
                if tool_name not in active_tool_names:
                    logger.debug(f"Skipping tool '{tool_name}' (not active in database)")
                    continue

                # Get description from database
                db_tool = next((t for t in active_tools if t.name == tool_name), None)
                final_description = db_tool.description if db_tool else _description

                # Register with FastMCP using the tool decorator
                # Note: Observability wrapping with *args/**kwargs doesn't work with FastMCP
                # TODO: Implement observability at handler level or use signature-preserving wrapper
                decorated_tool = mcp.tool(name=tool_name, description=final_description)(tool_func)

                # Store reference to prevent garbage collection
                if not hasattr(mcp, "_dynamic_tools"):
                    mcp._dynamic_tools = []
                mcp._dynamic_tools.append(decorated_tool)

                registered_count += 1
                logger.info(f"Registered tool: {tool_name}")

            logger.info(f"Successfully registered {registered_count} tools for domain '{domain}'")

            # Warn about tools in DB but not registered
            db_tool_names = {tool.name for tool in active_tools}
            registered_tool_names = {name for name, _, _ in registered_tools}
            missing_tools = db_tool_names - registered_tool_names
            if missing_tools:
                logger.warning(
                    f"Tools in database but not registered in code: {missing_tools}. "
                    f"These will not be available."
                )

    except Exception as e:
        logger.error(f"Failed to load tools from registry: {e}")
        raise


def _wrap_with_observability(
    tool_func: Callable[..., Any],
    tool_name: str,
    domain: str,
    transport: str,
) -> Callable[..., Any]:
    """Wrap tool function with observability tracing.

    Args:
        tool_func: Original tool function
        tool_name: Name of the tool
        domain: Domain the tool belongs to
        transport: Transport protocol

    Returns:
        Wrapped function with observability
    """

    async def traced_tool(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Tool wrapper with observability."""
        # Build parameters dict for tracing
        parameters = kwargs.copy() if kwargs else {}
        if args:
            # Map positional args to parameter names
            sig = inspect.signature(tool_func)
            param_names = list(sig.parameters.keys())
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
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                trace_ctx["status"] = "error"
                trace_ctx["error_type"] = type(e).__name__
                trace_ctx["error_message"] = str(e)
                return {"success": False, "error": str(e)}

    return traced_tool

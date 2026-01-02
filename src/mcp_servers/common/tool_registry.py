"""Tool registry for decorator-based tool registration.

This module provides a registry pattern that allows domain-specific servers
to register tools using @mcp.tool() decorators while maintaining compatibility
with JSON config-driven enable/disable functionality.

The registry now uses a JSON configuration file (config/tools.json) instead of
a database, making tool management simpler and version-controllable.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from fastmcp import FastMCP

from src.mcp_servers.common.config_loader import get_active_tools_for_domain


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
    config_path: str | Path = "config/tools.json",
) -> None:
    """Load tools from registry and register with FastMCP, filtered by JSON config.

    This function:
    1. Gets all registered tools for the domain from TOOL_REGISTRY
    2. Checks JSON config to see which tools are active
    3. Registers only active tools with FastMCP

    Note: Observability tracing is automatically applied via ObservabilityMiddleware
    which is registered in base_server.py. All tool executions are wrapped with
    comprehensive tracing, metrics, and audit logging.

    Args:
        mcp: FastMCP server instance to register tools with
        domain: Domain to load tools for
        transport: Transport protocol being used (stdio, http, sse) - kept for
                   backward compatibility but not used (observability is via middleware)
        config_path: Path to tools configuration JSON file

    Raises:
        Exception: If tool loading fails
    """
    if domain not in TOOL_REGISTRY:
        logger.warning(f"No tools registered for domain '{domain}'")
        return

    try:
        # Get active tools from JSON config for this domain
        active_tools_config = get_active_tools_for_domain(domain, config_path)
        active_tool_names = {tool.name for tool in active_tools_config}

        # Get registered tools for this domain
        registered_tools = TOOL_REGISTRY.get(domain, [])

        logger.info(
            f"Loading {len(registered_tools)} registered tools for domain '{domain}' "
            f"({len(active_tool_names)} active in config)"
        )

        # Register each tool that is both registered in code and active in config
        registered_count = 0
        for tool_name, tool_func, code_description in registered_tools:
            if tool_name not in active_tool_names:
                logger.debug(f"Skipping tool '{tool_name}' (not active in config)")
                continue

            # Get description from config (prefer config over code)
            config_tool = next((t for t in active_tools_config if t.name == tool_name), None)
            final_description = config_tool.description if config_tool else code_description

            # Register with FastMCP using the tool decorator
            # Observability is automatically applied via ObservabilityMiddleware
            # Apply the tool decorator to the tool function
            decorated_tool = mcp.tool(name=tool_name, description=final_description)(tool_func)

            # Store reference to prevent garbage collection
            if not hasattr(mcp, "_dynamic_tools"):
                cast(Any, mcp)._dynamic_tools = []
            dynamic_tools = getattr(mcp, "_dynamic_tools", [])
            if isinstance(dynamic_tools, list):
                dynamic_tools.append(decorated_tool)

            registered_count += 1
            logger.info(f"Registered tool: {tool_name}")

        logger.info(f"Successfully registered {registered_count} tools for domain '{domain}'")

        # Warn about tools in config but not registered
        config_tool_names = {tool.name for tool in active_tools_config}
        registered_tool_names = {name for name, _, _ in registered_tools}
        missing_tools = config_tool_names - registered_tool_names
        if missing_tools:
            logger.warning(
                f"Tools in config but not registered in code: {missing_tools}. "
                f"These will not be available."
            )

    except Exception as e:
        logger.error(f"Failed to load tools from registry: {e}")
        raise

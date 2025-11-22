"""Tool definitions for general domain using decorator-based registration."""

from typing import Any

from src.core.services.general.tool_handlers_service import (
    calculator_add_handler,
    echo_handler,
)
from src.mcp_servers.common.base_server import create_mcp_server
from src.mcp_servers.common.tool_registry import register_tool


# Create FastMCP instance for this domain
mcp = create_mcp_server(domain="general")


@register_tool(
    domain="general",
    tool_name="echo",
    description="Echo back the provided text",
)
async def echo(text: str) -> dict[str, Any]:
    """Echo back the provided text.

    Useful for testing and simple text repetition.

    Args:
        text: The text to echo back

    Returns:
        Dictionary with success status and echoed message
    """
    return echo_handler({"text": text})


@register_tool(
    domain="general",
    tool_name="calculator_add",
    description="Add two numbers together",
)
async def calculator_add(a: float, b: float) -> dict[str, Any]:
    """Add two numbers together.

    Performs simple addition operation.

    Args:
        a: First number
        b: Second number

    Returns:
        Dictionary with success status, operation details, and result
    """
    return calculator_add_handler({"a": a, "b": b})

"""MCP tools implementation."""

import logging
from typing import Any

from src.core.services.tool_handlers import calculator_add_handler, echo_handler
from src.mcp_servers.general.server import mcp


logger = logging.getLogger(__name__)


@mcp.tool(name="echo", description="Echo back the provided text")  # type: ignore[misc]
async def echo(text: str) -> dict[str, Any]:
    """Echo back the provided text.

    Args:
        text: The text to echo back

    Returns:
        Dictionary with success status and echoed message
    """
    try:
        result = echo_handler({"text": text})
        return result
    except Exception as e:
        logger.error(f"Echo tool failed: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool(name="calculator_add", description="Add two numbers together")  # type: ignore[misc]
async def calculator_add(a: float, b: float) -> dict[str, Any]:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Dictionary with success status and result
    """
    try:
        result = calculator_add_handler({"a": a, "b": b})
        return result
    except Exception as e:
        logger.error(f"Calculator add tool failed: {e}")
        return {"success": False, "error": str(e)}


async def load_and_register_tools() -> None:
    """Verify tools are available.

    Note: Tools are statically registered above with @mcp.tool decorators.
    This function logs the available tools.
    """
    logger.info("MCP tools registered: echo, calculator_add")

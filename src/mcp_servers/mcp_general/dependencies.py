"""Dependency injection for MCP server."""

from collections.abc import AsyncGenerator
from typing import Any

from src.core.services.common.tool_service import TOOL_HANDLERS


async def get_tool_handlers() -> AsyncGenerator[dict[str, Any], None]:
    """Get tool handler registry.

    Yields:
        Mapping of handler name -> handler function
    """
    yield TOOL_HANDLERS

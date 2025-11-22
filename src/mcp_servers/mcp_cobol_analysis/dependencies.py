"""Dependency injection for COBOL Analysis MCP server."""

from collections.abc import AsyncGenerator

from src.core.database import get_session
from src.core.services.common.tool_service_service import ToolService


async def get_tool_service() -> AsyncGenerator[ToolService, None]:
    """Get tool service with database session.

    Yields:
        ToolService instance
    """
    async for session in get_session():
        yield ToolService(session)

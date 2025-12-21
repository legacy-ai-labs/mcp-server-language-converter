"""Tool service for business logic operations.

NOTE: This file contains legacy database-driven tool service code.
The project has migrated to JSON config-based tool loading.
Database-related functionality is commented out until migration is complete.
"""

from typing import Any

# from sqlalchemy.ext.asyncio import AsyncSession
#
# from src.core.exceptions import (
#     ToolHandlerError,
#     ToolHandlerNotFoundError,
#     ToolNotFoundError,
#     ValidationError,
# )
# from src.core.models.tool_model import Tool  # File deleted - migrated to JSON config
# from src.core.repositories.tool_repository import ToolRepository  # Deleted
# from src.core.schemas.tool_schema import ToolCreate, ToolResponse, ToolUpdate
from src.core.services.cobol_analysis.tool_handlers_service import (
    TOOL_HANDLERS as COBOL_HANDLERS,
)
from src.core.services.general.tool_handlers_service import (
    TOOL_HANDLERS as GENERAL_HANDLERS,
)


# Merge all tool handlers from different domains
TOOL_HANDLERS = {**GENERAL_HANDLERS, **COBOL_HANDLERS}


def get_handler(handler_name: str) -> Any | None:
    """Get a tool handler by name from all domains.

    Args:
        handler_name: Name of the handler

    Returns:
        Handler function or None if not found
    """
    return TOOL_HANDLERS.get(handler_name)


# NOTE: ToolService class removed - depends on deleted database models
# The project has migrated to JSON config-based tool loading
# Legacy ToolService class code has been removed as it depended on:
# - ToolRepository (deleted)
# - Tool model (deleted)
# - Database-based tool management (replaced with JSON config)

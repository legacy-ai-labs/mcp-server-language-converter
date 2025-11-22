"""Tool service for business logic operations."""

from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    ToolHandlerError,
    ToolHandlerNotFoundError,
    ToolNotFoundError,
    ValidationError,
)
from src.core.models.tool_model import Tool
from src.core.repositories.tool_repository import ToolRepository
from src.core.schemas.tool_schema import ToolCreate, ToolResponse, ToolUpdate
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


class ToolService:
    """Service for tool-related business logic."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize tool service.

        Args:
            session: Database session
        """
        self.repository = ToolRepository(session)

    async def create_tool(self, tool_data: ToolCreate) -> ToolResponse:
        """Create a new tool.

        Args:
            tool_data: Tool creation data

        Returns:
            Created tool response

        Raises:
            ValidationError: If validation fails
            ToolHandlerNotFoundError: If handler doesn't exist
        """
        # Validate handler exists
        if not get_handler(tool_data.handler_name):
            raise ToolHandlerNotFoundError(
                f"Handler '{tool_data.handler_name}' not found in registry"
            )

        # Check if tool with same name already exists
        existing_tool = await self.repository.get_by_name(tool_data.name)
        if existing_tool:
            raise ValidationError(f"Tool with name '{tool_data.name}' already exists")

        # Create tool
        tool: Tool = await self.repository.create(tool_data.model_dump())
        return ToolResponse.model_validate(tool)

    async def get_tool(self, tool_id: int) -> ToolResponse:
        """Get a tool by ID.

        Args:
            tool_id: Tool ID

        Returns:
            Tool response

        Raises:
            ToolNotFoundError: If tool not found
        """
        tool = await self.repository.get_by_id(tool_id)
        if not tool:
            raise ToolNotFoundError(f"Tool with ID {tool_id} not found")
        return ToolResponse.model_validate(tool)

    async def get_tool_by_name(self, name: str) -> ToolResponse:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool response

        Raises:
            ToolNotFoundError: If tool not found
        """
        tool = await self.repository.get_by_name(name)
        if not tool:
            raise ToolNotFoundError(f"Tool with name '{name}' not found")
        return ToolResponse.model_validate(tool)

    async def list_tools(self, active_only: bool = False) -> list[ToolResponse]:
        """List all tools.

        Args:
            active_only: If True, only return active tools

        Returns:
            List of tool responses
        """
        if active_only:
            tools = await self.repository.list_active()
        else:
            tools = await self.repository.list_all()
        return [ToolResponse.model_validate(tool) for tool in tools]

    async def update_tool(self, tool_id: int, tool_data: ToolUpdate) -> ToolResponse:
        """Update a tool.

        Args:
            tool_id: Tool ID
            tool_data: Tool update data

        Returns:
            Updated tool response

        Raises:
            ToolNotFoundError: If tool not found
            ToolHandlerNotFoundError: If new handler doesn't exist
        """
        # Validate handler exists if being updated
        if tool_data.handler_name and not get_handler(tool_data.handler_name):
            raise ToolHandlerNotFoundError(
                f"Handler '{tool_data.handler_name}' not found in registry"
            )

        tool = await self.repository.update(tool_id, tool_data.model_dump(exclude_unset=True))
        if not tool:
            raise ToolNotFoundError(f"Tool with ID {tool_id} not found")
        return ToolResponse.model_validate(tool)

    async def delete_tool(self, tool_id: int, soft: bool = True) -> bool:
        """Delete a tool.

        Args:
            tool_id: Tool ID
            soft: If True, perform soft delete (set is_active=False)

        Returns:
            True if deleted

        Raises:
            ToolNotFoundError: If tool not found
        """
        if soft:
            success = await self.repository.soft_delete(tool_id)
        else:
            success = await self.repository.delete(tool_id)

        if not success:
            raise ToolNotFoundError(f"Tool with ID {tool_id} not found")
        return True

    async def execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name.

        Args:
            tool_name: Tool name
            parameters: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If tool not found or not active
            ToolHandlerNotFoundError: If handler not found
            ToolHandlerError: If handler execution fails
        """
        # Get tool from database
        tool = await self.repository.get_by_name(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")

        if not tool.is_active:
            raise ToolNotFoundError(f"Tool '{tool_name}' is not active")

        # Get handler
        handler = get_handler(tool.handler_name)
        if not handler:
            raise ToolHandlerNotFoundError(f"Handler '{tool.handler_name}' not found in registry")

        # Execute handler
        try:
            result = handler(parameters)
            return cast(dict[str, Any], result)
        except Exception as e:
            raise ToolHandlerError(f"Handler execution failed: {e}") from e

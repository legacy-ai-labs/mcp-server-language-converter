"""Seed initial tools into the database."""

import asyncio
import logging

from src.core.database import async_session_factory
from src.core.schemas.tool_schema import ToolCreate
from src.core.services.tool_service_service import ToolService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


INITIAL_TOOLS = [
    ToolCreate(
        name="echo",
        description="Echo back the provided text. Useful for testing and simple text repetition.",
        handler_name="echo_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to echo back",
                }
            },
            "required": ["text"],
        },
        category="utility",
        domain="general",
        is_active=True,
    ),
    ToolCreate(
        name="calculator_add",
        description="Add two numbers together. Performs simple addition operation.",
        handler_name="calculator_add_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number to add",
                },
                "b": {
                    "type": "number",
                    "description": "Second number to add",
                },
            },
            "required": ["a", "b"],
        },
        category="calculation",
        domain="general",
        is_active=True,
    ),
]


async def seed_tools() -> None:
    """Seed initial tools into the database."""
    logger.info(f"Seeding {len(INITIAL_TOOLS)} tools...")

    for tool_data in INITIAL_TOOLS:
        # Use a new session for each tool to avoid transaction issues
        async with async_session_factory() as session:
            service = ToolService(session)
            try:
                # Check if tool already exists
                existing_tool = await service.get_tool_by_name(tool_data.name)
                logger.info(f"Tool '{tool_data.name}' already exists (ID: {existing_tool.id})")
                continue
            except Exception:  # nosec B110
                # Tool doesn't exist, proceed with creation
                pass

            try:
                # Create tool
                tool = await service.create_tool(tool_data)
                logger.info(f"Created tool: {tool.name} (ID: {tool.id})")
            except Exception as e:
                logger.error(f"Failed to create tool '{tool_data.name}': {e}")

    logger.info("Tool seeding complete!")


async def main() -> None:
    """Main function to run seeding."""
    await seed_tools()


if __name__ == "__main__":
    asyncio.run(main())

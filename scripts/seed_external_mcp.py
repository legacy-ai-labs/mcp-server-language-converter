"""Seed external MCP servers configuration."""

import asyncio
import json
import logging

from src.core.database import async_session_factory
from src.core.repositories.external_mcp_repository import ExternalMCPServerRepository
from src.core.schemas.external_mcp import ExternalMCPServerCreate


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example external MCP servers configuration
EXTERNAL_MCP_SERVERS = [
    ExternalMCPServerCreate(
        name="best_buy",
        display_name="Best Buy MCP Server",
        command=json.dumps(["python", "-m", "best_buy_mcp"]),
        working_directory="/path/to/best_buy_mcp",
        is_active=False,  # Disabled by default since it doesn't exist
        connection_timeout=30,
        retry_attempts=3,
    ),
    ExternalMCPServerCreate(
        name="github",
        display_name="GitHub MCP Server",
        command=json.dumps(["python", "-m", "github_mcp"]),
        working_directory="/path/to/github_mcp",
        is_active=False,  # Disabled by default since it doesn't exist
        connection_timeout=30,
        retry_attempts=3,
    ),
    ExternalMCPServerCreate(
        name="slack",
        display_name="Slack MCP Server",
        command=json.dumps(["python", "-m", "slack_mcp"]),
        working_directory="/path/to/slack_mcp",
        is_active=False,  # Disabled by default since it doesn't exist
        connection_timeout=30,
        retry_attempts=3,
    ),
]


async def seed_external_mcp_servers() -> None:
    """Seed external MCP servers configuration."""
    logger.info(f"Seeding {len(EXTERNAL_MCP_SERVERS)} external MCP servers...")

    async with async_session_factory() as session:
        server_repo = ExternalMCPServerRepository(session)

        for server_data in EXTERNAL_MCP_SERVERS:
            try:
                # Check if server already exists
                existing_server = await server_repo.get_by_name(server_data.name)
                if existing_server:
                    logger.info(
                        f"External MCP server '{server_data.name}' already exists (ID: {existing_server.id})"
                    )
                    continue

                # Create server
                server = await server_repo.create(server_data.model_dump())
                logger.info(f"Created external MCP server: {server.name} (ID: {server.id})")

            except Exception as e:
                logger.error(f"Failed to create external MCP server '{server_data.name}': {e}")

    logger.info("External MCP server seeding complete!")


async def main() -> None:
    """Main function to run seeding."""
    await seed_external_mcp_servers()


if __name__ == "__main__":
    asyncio.run(main())

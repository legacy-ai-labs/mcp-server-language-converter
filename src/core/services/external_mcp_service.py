"""External MCP orchestration service."""

import json
import logging
from datetime import datetime
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.core.models.external_mcp import ExternalMCPServer, ExternalMCPStatus, ExternalMCPTool
from src.core.repositories.external_mcp_repository import (
    ExternalMCPServerRepository,
    ExternalMCPStatusRepository,
    ExternalMCPToolRepository,
)
from src.core.schemas.external_mcp import ExternalMCPToolCreate


logger = logging.getLogger(__name__)


class ExternalMCPService:
    """Service for managing external MCP servers and tools."""

    def __init__(self, session: Any) -> None:
        """Initialize external MCP service.

        Args:
            session: Database session
        """
        self.session = session
        self.server_repo = ExternalMCPServerRepository(session)
        self.tool_repo = ExternalMCPToolRepository(session)
        self.status_repo = ExternalMCPStatusRepository(session)

    async def discover_all_external_tools(self) -> dict[str, list[dict[str, Any]]]:
        """Discover tools from all active external MCP servers.

        Returns:
            Dictionary mapping server names to their discovered tools
        """
        servers = await self.server_repo.list_active()
        all_tools = {}

        for server in servers:
            try:
                tools = await self._discover_server_tools(server)
                all_tools[server.name] = tools
                await self._update_server_status(server.id, "connected")
                logger.info(f"Discovered {len(tools)} tools from {server.name}")
            except Exception as e:
                await self._update_server_status(server.id, "error", str(e))
                logger.error(f"Failed to discover tools from {server.name}: {e}")

        return all_tools

    async def _discover_server_tools(self, server: ExternalMCPServer) -> list[dict[str, Any]]:
        """Discover tools from a specific external MCP server.

        Args:
            server: External MCP server configuration

        Returns:
            List of discovered tool data
        """
        import asyncio

        command = json.loads(server.command)
        server_params = StdioServerParameters(
            command=command,
            cwd=server.working_directory,
        )

        tools = []
        try:
            # Use asyncio.wait_for to implement timeout
            async with asyncio.timeout(server.connection_timeout):
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Get available tools
                        mcp_tools = await session.list_tools()

                        for tool in mcp_tools:
                            tool_data = {
                                "server_id": server.id,
                                "name": tool.name,
                                "full_name": f"{server.name}_{tool.name}",
                                "description": tool.description,
                                "parameters_schema": tool.inputSchema,
                            }
                            tools.append(tool_data)

                            # Store/update in database
                            await self._store_external_tool(tool_data)

        except TimeoutError:
            raise Exception(
                f"Connection timeout after {server.connection_timeout} seconds"
            ) from None
        except Exception as e:
            raise Exception(f"Failed to connect to {server.name}: {e}") from e

        return tools

    async def _store_external_tool(self, tool_data: dict[str, Any]) -> None:
        """Store or update external tool in database.

        Args:
            tool_data: Tool data to store
        """
        existing_tool = await self.tool_repo.get_by_full_name(tool_data["full_name"])

        if existing_tool:
            # Update existing tool
            await self.tool_repo.update(
                existing_tool.id,
                {
                    "description": tool_data["description"],
                    "parameters_schema": tool_data["parameters_schema"],
                    "last_discovered": datetime.utcnow(),
                },
            )
        else:
            # Create new tool
            tool_create = ExternalMCPToolCreate(**tool_data)
            await self.tool_repo.create(tool_create.model_dump())

    async def _update_server_status(
        self,
        server_id: int,
        status: str,
        error_message: str | None = None,
        response_time_ms: int | None = None,
    ) -> None:
        """Update external MCP server status.

        Args:
            server_id: Server ID
            status: Status value
            error_message: Error message if applicable
            response_time_ms: Response time in milliseconds
        """
        status_data = {
            "server_id": server_id,
            "status": status,
            "error_message": error_message,
            "response_time_ms": response_time_ms,
        }

        await self.status_repo.create(status_data)

    async def get_active_external_tools(self) -> list[ExternalMCPTool]:
        """Get all active external MCP tools.

        Returns:
            List of active external MCP tools
        """
        return await self.tool_repo.list_active()

    async def call_external_tool(
        self, server: ExternalMCPServer, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool on an external MCP server.

        Args:
            server: External MCP server configuration
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        import asyncio

        command = json.loads(server.command)
        server_params = StdioServerParameters(
            command=command,
            cwd=server.working_directory,
        )

        try:
            async with asyncio.timeout(server.connection_timeout):
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Call the tool
                        result = await session.call_tool(tool_name, arguments)
                        return dict(result) if result else {}

        except TimeoutError:
            raise Exception(
                f"Tool call timeout after {server.connection_timeout} seconds"
            ) from None
        except Exception as e:
            raise Exception(f"Failed to call tool {tool_name} on {server.name}: {e}") from e

    async def get_server_by_id(self, server_id: int) -> ExternalMCPServer | None:
        """Get external MCP server by ID.

        Args:
            server_id: Server ID

        Returns:
            External MCP server or None if not found
        """
        return await self.server_repo.get_by_id(server_id)

    async def get_server_health_status(self, server_id: int) -> ExternalMCPStatus | None:
        """Get latest health status for a server.

        Args:
            server_id: Server ID

        Returns:
            Latest health status or None if not found
        """
        return await self.status_repo.get_latest_by_server_id(server_id)

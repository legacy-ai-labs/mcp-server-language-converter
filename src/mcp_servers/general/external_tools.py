"""External MCP tools loader for dynamic registration."""

import logging
from typing import Any

from src.core.database import async_session_factory
from src.core.models.external_mcp import ExternalMCPTool
from src.core.services.external_mcp_service import ExternalMCPService
from src.mcp_servers.general.server import mcp


logger = logging.getLogger(__name__)


class ExternalToolsLoader:
    """Loader for external MCP tools."""

    def __init__(self) -> None:
        """Initialize external tools loader."""
        self.external_service: ExternalMCPService | None = None

    async def load_external_tools(self) -> None:
        """Load external tools from database and register them with FastMCP."""
        try:
            async with async_session_factory() as session:
                self.external_service = ExternalMCPService(session)

                # Get all active external tools
                external_tools = await self.external_service.get_active_external_tools()

                logger.info(f"Loading {len(external_tools)} external tools...")

                for tool in external_tools:
                    try:
                        await self._register_external_tool(tool)
                        logger.info(f"Registered external tool: {tool.full_name}")
                    except Exception as e:
                        logger.error(f"Failed to register external tool {tool.full_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to load external tools: {e}")
            raise

    async def _register_external_tool(self, tool: ExternalMCPTool) -> None:
        """Register a single external tool with FastMCP.

        Args:
            tool: External MCP tool to register
        """
        if not self.external_service:
            raise RuntimeError("External service not initialized")

        server = await self.external_service.get_server_by_id(tool.server_id)
        if not server:
            logger.error(f"Server not found for tool {tool.full_name}")
            return

        async def external_tool_wrapper(**kwargs: Any) -> dict[str, Any]:
            """Wrapper that calls external MCP server.

            Args:
                kwargs: Tool arguments

            Returns:
                Tool execution result
            """
            try:
                if self.external_service:
                    result = await self.external_service.call_external_tool(
                        server, tool.name, kwargs
                    )
                else:
                    raise RuntimeError("External service not initialized")
                return result
            except Exception as e:
                logger.error(f"External tool {tool.full_name} failed: {e}")
                return {"success": False, "error": str(e)}

        # Register with FastMCP
        decorated_tool = mcp.tool(name=tool.full_name, description=tool.description)(
            external_tool_wrapper
        )

        # Store reference to prevent garbage collection
        if not hasattr(mcp, "_external_tools"):
            mcp._external_tools = []
        mcp._external_tools.append(decorated_tool)

    async def discover_and_load_tools(self) -> None:
        """Discover tools from external MCP servers and load them.

        This method:
        1. Discovers tools from all active external MCP servers
        2. Stores discovered tools in the database
        3. Registers them with FastMCP
        """
        try:
            async with async_session_factory() as session:
                self.external_service = ExternalMCPService(session)

                # Discover tools from all external servers
                await self.external_service.discover_all_external_tools()

                # Load the discovered tools
                await self.load_external_tools()

        except Exception as e:
            logger.error(f"Failed to discover and load external tools: {e}")
            raise

    async def get_external_tools_summary(self) -> dict[str, Any]:
        """Get summary of external tools.

        Returns:
            Dictionary with external tools summary
        """
        try:
            async with async_session_factory() as session:
                self.external_service = ExternalMCPService(session)

                external_tools = await self.external_service.get_active_external_tools()
                servers = await self.external_service.server_repo.list_active()

                summary: dict[str, Any] = {
                    "total_external_tools": len(external_tools),
                    "total_external_servers": len(servers),
                    "tools_by_server": {},
                }

                for server in servers:
                    if self.external_service:
                        server_tools = (
                            await self.external_service.tool_repo.get_active_by_server_id(server.id)
                        )
                        summary["tools_by_server"][server.name] = {
                            "count": len(server_tools),
                            "tools": [tool.full_name for tool in server_tools],
                        }

                return summary

        except Exception as e:
            logger.error(f"Failed to get external tools summary: {e}")
            return {"error": str(e)}

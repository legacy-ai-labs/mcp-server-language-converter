"""External MCP repository for database operations."""


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.external_mcp import ExternalMCPServer, ExternalMCPStatus, ExternalMCPTool
from src.core.repositories.base import BaseRepository


class ExternalMCPServerRepository(BaseRepository[ExternalMCPServer]):
    """Repository for external MCP server operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize external MCP server repository.

        Args:
            session: Database session
        """
        super().__init__(ExternalMCPServer, session)

    async def get_by_name(self, name: str) -> ExternalMCPServer | None:
        """Get external MCP server by name.

        Args:
            name: Server name

        Returns:
            External MCP server instance or None if not found
        """
        result = await self.session.execute(
            select(ExternalMCPServer).where(ExternalMCPServer.name == name)
        )
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def list_active(self) -> list[ExternalMCPServer]:
        """List all active external MCP servers.

        Returns:
            List of active external MCP server instances
        """
        result = await self.session.execute(
            select(ExternalMCPServer).where(ExternalMCPServer.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def activate(self, id_: int) -> bool:
        """Activate an external MCP server.

        Args:
            id_: Server ID

        Returns:
            True if activated, False if not found
        """
        server = await self.get_by_id(id_)
        if not server:
            return False

        server.is_active = True
        await self.session.commit()
        return True

    async def deactivate(self, id_: int) -> bool:
        """Deactivate an external MCP server.

        Args:
            id_: Server ID

        Returns:
            True if deactivated, False if not found
        """
        server = await self.get_by_id(id_)
        if not server:
            return False

        server.is_active = False
        await self.session.commit()
        return True


class ExternalMCPToolRepository(BaseRepository[ExternalMCPTool]):
    """Repository for external MCP tool operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize external MCP tool repository.

        Args:
            session: Database session
        """
        super().__init__(ExternalMCPTool, session)

    async def get_by_full_name(self, full_name: str) -> ExternalMCPTool | None:
        """Get external MCP tool by full name.

        Args:
            full_name: Full tool name with namespace

        Returns:
            External MCP tool instance or None if not found
        """
        result = await self.session.execute(
            select(ExternalMCPTool).where(ExternalMCPTool.full_name == full_name)
        )
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def list_active(self) -> list[ExternalMCPTool]:
        """List all active external MCP tools.

        Returns:
            List of active external MCP tool instances
        """
        result = await self.session.execute(
            select(ExternalMCPTool).where(ExternalMCPTool.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_by_server_id(self, server_id: int) -> list[ExternalMCPTool]:
        """Get external MCP tools by server ID.

        Args:
            server_id: Server ID

        Returns:
            List of external MCP tool instances
        """
        result = await self.session.execute(
            select(ExternalMCPTool).where(ExternalMCPTool.server_id == server_id)
        )
        return list(result.scalars().all())

    async def get_active_by_server_id(self, server_id: int) -> list[ExternalMCPTool]:
        """Get active external MCP tools by server ID.

        Args:
            server_id: Server ID

        Returns:
            List of active external MCP tool instances
        """
        result = await self.session.execute(
            select(ExternalMCPTool).where(
                ExternalMCPTool.server_id == server_id,
                ExternalMCPTool.is_active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def activate(self, id_: int) -> bool:
        """Activate an external MCP tool.

        Args:
            id_: Tool ID

        Returns:
            True if activated, False if not found
        """
        tool = await self.get_by_id(id_)
        if not tool:
            return False

        tool.is_active = True
        await self.session.commit()
        return True

    async def deactivate(self, id_: int) -> bool:
        """Deactivate an external MCP tool.

        Args:
            id_: Tool ID

        Returns:
            True if deactivated, False if not found
        """
        tool = await self.get_by_id(id_)
        if not tool:
            return False

        tool.is_active = False
        await self.session.commit()
        return True


class ExternalMCPStatusRepository(BaseRepository[ExternalMCPStatus]):
    """Repository for external MCP status operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize external MCP status repository.

        Args:
            session: Database session
        """
        super().__init__(ExternalMCPStatus, session)

    async def get_latest_by_server_id(self, server_id: int) -> ExternalMCPStatus | None:
        """Get latest status for a server.

        Args:
            server_id: Server ID

        Returns:
            Latest external MCP status or None if not found
        """
        result = await self.session.execute(
            select(ExternalMCPStatus)
            .where(ExternalMCPStatus.server_id == server_id)
            .order_by(ExternalMCPStatus.last_check.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def get_by_status(self, status: str) -> list[ExternalMCPStatus]:
        """Get statuses by status value.

        Args:
            status: Status value

        Returns:
            List of external MCP status instances
        """
        result = await self.session.execute(
            select(ExternalMCPStatus).where(ExternalMCPStatus.status == status)
        )
        return list(result.scalars().all())

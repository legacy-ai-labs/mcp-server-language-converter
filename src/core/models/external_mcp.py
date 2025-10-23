"""External MCP server and tool models."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.core.database import Base


class ExternalMCPServer(Base):
    """External MCP server configuration model."""

    __tablename__ = "external_mcp_servers"  # type: ignore[assignment]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    working_directory: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    connection_timeout: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    retry_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to external tools
    tools: Mapped[list["ExternalMCPTool"]] = relationship(
        "ExternalMCPTool", back_populates="server", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of the external MCP server."""
        return f"<ExternalMCPServer(id={self.id}, name='{self.name}', active={self.is_active})>"


class ExternalMCPTool(Base):
    """External MCP tool model."""

    __tablename__ = "external_mcp_tools"  # type: ignore[assignment]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("external_mcp_servers.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parameters_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_discovered: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to server
    server: Mapped["ExternalMCPServer"] = relationship("ExternalMCPServer", back_populates="tools")

    def __repr__(self) -> str:
        """String representation of the external MCP tool."""
        return (
            f"<ExternalMCPTool(id={self.id}, name='{self.full_name}', server_id={self.server_id})>"
        )


class ExternalMCPStatus(Base):
    """External MCP server status monitoring model."""

    __tablename__ = "external_mcp_status"  # type: ignore[assignment]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("external_mcp_servers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # connected, disconnected, error
    last_check: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationship to server
    server: Mapped["ExternalMCPServer"] = relationship("ExternalMCPServer")

    def __repr__(self) -> str:
        """String representation of the external MCP status."""
        return f"<ExternalMCPStatus(server_id={self.server_id}, status='{self.status}')>"

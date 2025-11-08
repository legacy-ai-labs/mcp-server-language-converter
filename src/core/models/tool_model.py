"""Tool database model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func

from src.core.database import Base


class Tool(Base):
    """Tool model representing an MCP tool stored in the database."""

    @declared_attr.directive  # type: ignore[misc]
    def __tablename__(cls) -> str:
        return "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    handler_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation of the tool."""
        return f"<Tool(id={self.id}, name='{self.name}', handler='{self.handler_name}')>"

"""Tool execution database model for observability and metrics."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func

from src.core.database import Base


class ToolExecution(Base):
    """Tool execution model for tracking all tool invocations.

    This model stores detailed execution records for observability, metrics,
    and debugging. It enables:
    - E2E tracing with correlation_id and session_id
    - Performance monitoring (latency percentiles, rates)
    - Error pattern detection
    - Audit trail for compliance
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "tool_executions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Tool identification
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Tracing - for distributed tracing and correlation
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Timing information
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Execution outcome
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # success, error, timeout
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution context (can be large, optional for privacy)
    input_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Transport and domain context
    transport: Mapped[str] = mapped_column(String(20), nullable=False)  # stdio, http, rest
    domain: Mapped[str] = mapped_column(String(50), nullable=False)

    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        # For querying tool metrics by status over time
        Index(
            "ix_tool_executions_tool_status_time",
            "tool_name",
            "status",
            "started_at",
        ),
        # For querying domain metrics
        Index(
            "ix_tool_executions_domain_time",
            "domain",
            "started_at",
        ),
        # For E2E tracing queries
        Index(
            "ix_tool_executions_correlation_session",
            "correlation_id",
            "session_id",
        ),
    )

    def __repr__(self) -> str:
        """String representation of the tool execution."""
        return (
            f"<ToolExecution(id={self.id}, tool='{self.tool_name}', "
            f"status='{self.status}', duration_ms={self.duration_ms})>"
        )

    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return bool(self.status == "success")

    @property
    def is_error(self) -> bool:
        """Check if execution resulted in error."""
        return bool(self.status == "error")

    @property
    def duration_seconds(self) -> float | None:
        """Get duration in seconds."""
        if self.duration_ms is None:
            return None
        return float(self.duration_ms / 1000.0)

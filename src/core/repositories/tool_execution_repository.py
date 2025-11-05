"""Repository for tool execution metrics and observability."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.tool_execution import ToolExecution


class ToolExecutionRepository:
    """Repository for tool execution operations and metrics queries.

    Provides methods for:
    - CRUD operations on tool executions
    - Metrics calculations (rates, percentiles, error patterns)
    - E2E tracing queries
    - Historical analysis
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def create(self, execution_data: dict[str, Any]) -> ToolExecution:
        """Create a new tool execution record.

        Args:
            execution_data: Dictionary containing execution details

        Returns:
            Created ToolExecution instance
        """
        execution = ToolExecution(**execution_data)
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def get_by_id(self, execution_id: int) -> ToolExecution | None:
        """Get tool execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            ToolExecution if found, None otherwise
        """
        result = await self.db.execute(
            select(ToolExecution).where(ToolExecution.id == execution_id)
        )
        execution: ToolExecution | None = result.scalar_one_or_none()
        return execution

    async def get_by_correlation_id(self, correlation_id: str) -> list[ToolExecution]:
        """Get all executions with the same correlation ID.

        Useful for E2E tracing across multiple tool calls.

        Args:
            correlation_id: Correlation ID to search for

        Returns:
            List of ToolExecution instances
        """
        result = await self.db.execute(
            select(ToolExecution)
            .where(ToolExecution.correlation_id == correlation_id)
            .order_by(ToolExecution.started_at)
        )
        return list(result.scalars().all())

    async def get_by_session_id(self, session_id: str, limit: int = 100) -> list[ToolExecution]:
        """Get executions from a specific session.

        Args:
            session_id: Session ID to search for
            limit: Maximum number of results

        Returns:
            List of ToolExecution instances
        """
        result = await self.db.execute(
            select(ToolExecution)
            .where(ToolExecution.session_id == session_id)
            .order_by(ToolExecution.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_by_tool(self, tool_name: str, limit: int = 100) -> list[ToolExecution]:
        """Get recent executions for a specific tool.

        Args:
            tool_name: Name of the tool
            limit: Maximum number of results

        Returns:
            List of ToolExecution instances
        """
        result = await self.db.execute(
            select(ToolExecution)
            .where(ToolExecution.tool_name == tool_name)
            .order_by(ToolExecution.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        tool_name: str | None = None,
    ) -> list[ToolExecution]:
        """Get executions within a time range.

        Args:
            start_time: Start of time range
            end_time: End of time range
            tool_name: Optional tool name filter

        Returns:
            List of ToolExecution instances
        """
        query = select(ToolExecution).where(
            ToolExecution.started_at >= start_time,
            ToolExecution.started_at <= end_time,
        )

        if tool_name:
            query = query.where(ToolExecution.tool_name == tool_name)

        query = query.order_by(ToolExecution.started_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_status(
        self, tool_name: str | None = None, start_time: datetime | None = None
    ) -> dict[str, int]:
        """Count executions by status.

        Args:
            tool_name: Optional tool name filter
            start_time: Optional start time filter

        Returns:
            Dictionary mapping status to count
        """
        query = select(ToolExecution.status, func.count().label("count")).group_by(
            ToolExecution.status
        )

        if tool_name:
            query = query.where(ToolExecution.tool_name == tool_name)

        if start_time:
            query = query.where(ToolExecution.started_at >= start_time)

        result = await self.db.execute(query)
        rows = result.fetchall()

        return {str(row[0]): int(row[1]) for row in rows}

    async def get_tool_stats(
        self,
        tool_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Get statistics for a tool within a time range.

        Args:
            tool_name: Name of the tool
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary with statistics (total, success rate, avg duration, etc.)
        """
        query = select(
            func.count().label("total_calls"),
            func.count().filter(ToolExecution.status == "success").label("success_count"),
            func.count().filter(ToolExecution.status == "error").label("error_count"),
            func.avg(ToolExecution.duration_ms).label("avg_duration_ms"),
            func.min(ToolExecution.duration_ms).label("min_duration_ms"),
            func.max(ToolExecution.duration_ms).label("max_duration_ms"),
        ).where(
            ToolExecution.tool_name == tool_name,
            ToolExecution.started_at >= start_time,
            ToolExecution.started_at <= end_time,
        )

        result = await self.db.execute(query)
        row = result.fetchone()

        if not row or row.total_calls == 0:
            return {
                "total_calls": 0,
                "success_count": 0,
                "error_count": 0,
                "error_rate_pct": 0.0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": 0.0,
                "max_duration_ms": 0.0,
            }

        return {
            "total_calls": row.total_calls,
            "success_count": row.success_count,
            "error_count": row.error_count,
            "error_rate_pct": (row.error_count / row.total_calls * 100)
            if row.total_calls > 0
            else 0.0,
            "avg_duration_ms": float(row.avg_duration_ms) if row.avg_duration_ms else 0.0,
            "min_duration_ms": float(row.min_duration_ms) if row.min_duration_ms else 0.0,
            "max_duration_ms": float(row.max_duration_ms) if row.max_duration_ms else 0.0,
        }

    async def get_percentile_latencies(
        self,
        tool_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, float]:
        """Calculate percentile latencies from historical data.

        Note: This fetches all matching records to calculate percentiles.
        For large datasets, consider using database-specific percentile functions.

        Args:
            tool_name: Optional tool name filter
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Dictionary with percentile values (p50, p75, p90, p95, p99, max)
        """
        query = select(ToolExecution.duration_ms).where(
            ToolExecution.status == "success",
            ToolExecution.duration_ms.isnot(None),
        )

        if tool_name:
            query = query.where(ToolExecution.tool_name == tool_name)

        if start_time:
            query = query.where(ToolExecution.started_at >= start_time)

        if end_time:
            query = query.where(ToolExecution.started_at <= end_time)

        result = await self.db.execute(query)
        latencies = sorted([row[0] for row in result.fetchall()])

        if not latencies:
            return {
                "p50": 0.0,
                "p75": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "max": 0.0,
                "count": 0,
            }

        return {
            "p50": self._percentile(latencies, 50),
            "p75": self._percentile(latencies, 75),
            "p90": self._percentile(latencies, 90),
            "p95": self._percentile(latencies, 95),
            "p99": self._percentile(latencies, 99),
            "max": max(latencies),
            "count": len(latencies),
        }

    async def get_historical_rates(
        self,
        tool_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        bucket_size_minutes: int = 5,
    ) -> list[dict[str, Any]]:
        """Get request rates grouped by time buckets.

        Args:
            tool_name: Optional tool name filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            bucket_size_minutes: Size of time buckets in minutes

        Returns:
            List of dictionaries with time bucket and metrics
        """
        # Use PostgreSQL date_trunc for bucketing
        bucket_size = literal(f"{bucket_size_minutes} minutes")
        time_bucket = func.date_trunc(bucket_size, ToolExecution.started_at)

        query = (
            select(
                time_bucket.label("time_bucket"),
                func.count().label("total_calls"),
                func.count().filter(ToolExecution.status == "success").label("success_calls"),
                func.count().filter(ToolExecution.status == "error").label("error_calls"),
                func.avg(ToolExecution.duration_ms).label("avg_duration_ms"),
            )
            .group_by(time_bucket)
            .order_by(time_bucket.desc())
        )

        if tool_name:
            query = query.where(ToolExecution.tool_name == tool_name)

        if start_time:
            query = query.where(ToolExecution.started_at >= start_time)

        if end_time:
            query = query.where(ToolExecution.started_at <= end_time)

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            {
                "time_bucket": row.time_bucket,
                "total_calls": row.total_calls,
                "success_calls": row.success_calls,
                "error_calls": row.error_calls,
                "calls_per_second": row.total_calls / (bucket_size_minutes * 60),
                "error_rate_pct": (row.error_calls / row.total_calls * 100)
                if row.total_calls > 0
                else 0.0,
                "avg_duration_ms": float(row.avg_duration_ms) if row.avg_duration_ms else 0.0,
            }
            for row in rows
        ]

    @staticmethod
    def _percentile(sorted_values: list[float], p: int) -> float:
        """Calculate percentile from sorted values.

        Args:
            sorted_values: List of values in sorted order
            p: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * (p / 100)
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

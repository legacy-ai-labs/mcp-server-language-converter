"""Tests for repository layer."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repositories.tool_execution_repository import ToolExecutionRepository


@pytest.mark.asyncio
async def test_create_tool_execution(test_session: AsyncSession) -> None:
    """Test creating a tool execution record."""
    repository = ToolExecutionRepository(test_session)
    started_at = datetime.now(UTC)
    execution = await repository.create(
        {
            "tool_name": "test_tool",
            "correlation_id": "corr-1",
            "session_id": None,
            "started_at": started_at,
            "completed_at": started_at + timedelta(milliseconds=10),
            "duration_ms": 10.0,
            "status": "success",
            "error_type": None,
            "error_message": None,
            "input_params": {"x": 1},
            "output_data": {"ok": True},
            "transport": "stdio",
            "domain": "testing",
        }
    )

    assert execution.id is not None
    assert execution.tool_name == "test_tool"
    assert execution.correlation_id == "corr-1"
    assert execution.status == "success"


@pytest.mark.asyncio
async def test_get_by_id(test_session: AsyncSession) -> None:
    """Test getting a tool execution by ID."""
    repository = ToolExecutionRepository(test_session)
    started_at = datetime.now(UTC)
    created = await repository.create(
        {
            "tool_name": "test_tool",
            "correlation_id": "corr-2",
            "session_id": None,
            "started_at": started_at,
            "completed_at": None,
            "duration_ms": None,
            "status": "success",
            "error_type": None,
            "error_message": None,
            "input_params": None,
            "output_data": None,
            "transport": "stdio",
            "domain": "testing",
        }
    )

    execution = await repository.get_by_id(created.id)

    assert execution is not None
    assert execution.id == created.id
    assert execution.correlation_id == "corr-2"


@pytest.mark.asyncio
async def test_get_by_id_not_found(test_session: AsyncSession) -> None:
    """Test getting a non-existent execution."""
    repository = ToolExecutionRepository(test_session)
    execution = await repository.get_by_id(999)

    assert execution is None


@pytest.mark.asyncio
async def test_get_by_correlation_id(test_session: AsyncSession) -> None:
    """Test getting executions by correlation ID."""
    repository = ToolExecutionRepository(test_session)
    started_at = datetime.now(UTC)

    await repository.create(
        {
            "tool_name": "test_tool",
            "correlation_id": "corr-3",
            "session_id": None,
            "started_at": started_at,
            "completed_at": None,
            "duration_ms": None,
            "status": "success",
            "error_type": None,
            "error_message": None,
            "input_params": None,
            "output_data": None,
            "transport": "stdio",
            "domain": "testing",
        }
    )
    await repository.create(
        {
            "tool_name": "test_tool",
            "correlation_id": "corr-3",
            "session_id": None,
            "started_at": started_at + timedelta(seconds=1),
            "completed_at": None,
            "duration_ms": None,
            "status": "error",
            "error_type": "ValueError",
            "error_message": "boom",
            "input_params": None,
            "output_data": None,
            "transport": "stdio",
            "domain": "testing",
        }
    )

    executions = await repository.get_by_correlation_id("corr-3")
    assert len(executions) == 2


@pytest.mark.asyncio
async def test_get_recent_by_tool(test_session: AsyncSession) -> None:
    """Test getting recent executions by tool name."""
    repository = ToolExecutionRepository(test_session)
    base_time = datetime.now(UTC)

    await repository.create(
        {
            "tool_name": "recent_tool",
            "correlation_id": "corr-4a",
            "session_id": None,
            "started_at": base_time,
            "completed_at": None,
            "duration_ms": None,
            "status": "success",
            "error_type": None,
            "error_message": None,
            "input_params": None,
            "output_data": None,
            "transport": "stdio",
            "domain": "testing",
        }
    )
    await repository.create(
        {
            "tool_name": "recent_tool",
            "correlation_id": "corr-4b",
            "session_id": None,
            "started_at": base_time + timedelta(seconds=10),
            "completed_at": None,
            "duration_ms": None,
            "status": "success",
            "error_type": None,
            "error_message": None,
            "input_params": None,
            "output_data": None,
            "transport": "stdio",
            "domain": "testing",
        }
    )

    recent = await repository.get_recent_by_tool("recent_tool", limit=1)
    assert len(recent) == 1
    assert recent[0].correlation_id == "corr-4b"


@pytest.mark.asyncio
async def test_count_by_status(test_session: AsyncSession) -> None:
    """Test counting executions by status."""
    repository = ToolExecutionRepository(test_session)
    base_time = datetime.now(UTC)

    await repository.create(
        {
            "tool_name": "count_tool",
            "correlation_id": "corr-5a",
            "session_id": None,
            "started_at": base_time,
            "completed_at": None,
            "duration_ms": None,
            "status": "success",
            "error_type": None,
            "error_message": None,
            "input_params": None,
            "output_data": None,
            "transport": "stdio",
            "domain": "testing",
        }
    )
    await repository.create(
        {
            "tool_name": "count_tool",
            "correlation_id": "corr-5b",
            "session_id": None,
            "started_at": base_time + timedelta(seconds=1),
            "completed_at": None,
            "duration_ms": None,
            "status": "error",
            "error_type": "ValueError",
            "error_message": "boom",
            "input_params": None,
            "output_data": None,
            "transport": "stdio",
            "domain": "testing",
        }
    )

    counts = await repository.count_by_status(tool_name="count_tool")
    assert counts.get("success") == 1
    assert counts.get("error") == 1

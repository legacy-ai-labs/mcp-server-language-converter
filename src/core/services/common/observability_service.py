"""Observability and tracing for MCP tool executions.

This module provides comprehensive E2E tracing with:
- Correlation IDs for distributed tracing
- Session IDs for user tracking
- Automatic Prometheus metrics recording
- Database persistence for audit trail (via thread pool)
- Structured logging (TRACE_START/TRACE_END)

Note: Database writes are performed in a background thread pool to avoid
event loop mismatch issues with FastMCP's anyio-based transports.
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from src.core.config import get_settings
from src.core.database import sync_session_factory
from src.core.models.tool_execution_model import ToolExecution
from src.core.services.common.prometheus_metrics_service import PROMETHEUS_METRICS


logger = logging.getLogger(__name__)
settings = get_settings()

# Thread pool for database writes (avoids event loop issues)
# Using max_workers=3 to limit concurrent database writes
_db_write_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="observability_db_")


def calculate_payload_size(data: Any) -> int:
    """Calculate the size of a payload in bytes.

    Serializes the data to JSON and returns the byte length.
    Returns 0 if serialization fails.

    Args:
        data: Any JSON-serializable data

    Returns:
        Size in bytes, or 0 if calculation fails
    """
    if data is None:
        return 0
    try:
        return len(json.dumps(data, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return 0


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for E2E tracing.

    Returns:
        UUID string for correlation
    """
    return str(uuid.uuid4())


def get_correlation_id_from_context() -> str | None:
    """Get correlation ID from MCP context (if available).

    This is a placeholder for future MCP context integration.
    Currently returns None, which triggers generation of a new ID.

    Returns:
        Correlation ID from context or None
    """
    # TODO: Extract from MCP context when available
    return None


def get_session_id_from_context() -> str | None:
    """Get session ID from MCP context (if available).

    This is a placeholder for future MCP session tracking.

    Returns:
        Session ID from context or None
    """
    # TODO: Extract from MCP session when available
    return None


def _persist_execution_sync(
    tool_name: str,
    parameters: dict[str, Any],
    context: dict[str, Any],
    domain: str,
    transport: str,
) -> None:
    """Persist execution record to database synchronously (runs in thread pool).

    This function runs in a background thread pool to avoid event loop mismatch
    issues with FastMCP's anyio-based transports. Errors are logged but do not
    propagate back to the caller.

    Args:
        tool_name: Name of the tool
        parameters: Input parameters passed to the tool
        context: Execution context with timing and status
        domain: Domain the tool belongs to
        transport: Transport protocol used
    """
    if not settings.enable_execution_logging:
        return

    try:
        # Use synchronous session factory (safe in thread pool)
        with sync_session_factory() as session:
            # Create ToolExecution model instance directly
            execution = ToolExecution(
                tool_name=tool_name,
                correlation_id=context["correlation_id"],
                session_id=context.get("session_id"),
                started_at=context["started_at"],
                completed_at=context.get("completed_at"),
                duration_ms=context.get("duration_ms"),
                status=context["status"],
                error_type=context.get("error_type"),
                error_message=context.get("error_message"),
                input_params=parameters if settings.log_tool_inputs else None,
                output_data=context.get("output_data") if settings.log_tool_outputs else None,
                request_size_bytes=context.get("request_size_bytes"),
                response_size_bytes=context.get("response_size_bytes"),
                transport=transport,
                domain=domain,
            )

            session.add(execution)
            session.commit()

            logger.debug(
                f"Persisted execution: tool={tool_name} correlation_id={context['correlation_id']}"
            )

    except Exception as e:
        # Log errors but don't propagate (persistence is best-effort)
        logger.error(f"Failed to persist execution for {tool_name}: {e}", exc_info=True)


async def _persist_execution(
    tool_name: str,
    parameters: dict[str, Any],
    context: dict[str, Any],
    domain: str,
    transport: str,
) -> None:
    """Persist execution record to database asynchronously via thread pool.

    This function submits the database write to a background thread pool to
    avoid blocking the event loop and to work around event loop mismatch issues
    with FastMCP's anyio-based transports.

    Args:
        tool_name: Name of the tool
        parameters: Input parameters passed to the tool
        context: Execution context with timing and status
        domain: Domain the tool belongs to
        transport: Transport protocol used
    """
    if not settings.enable_execution_logging:
        return

    try:
        # Get current event loop
        loop = asyncio.get_running_loop()

        # Submit to thread pool - this works across all event loop implementations
        await loop.run_in_executor(
            _db_write_executor,
            _persist_execution_sync,
            tool_name,
            parameters,
            context,
            domain,
            transport,
        )

    except Exception as e:
        # Log errors but don't propagate (persistence is best-effort)
        logger.error(f"Failed to schedule database persistence for {tool_name}: {e}", exc_info=True)


@asynccontextmanager
async def trace_tool_execution(
    tool_name: str,
    parameters: dict[str, Any],
    domain: str,
    transport: str,
    correlation_id: str | None = None,
    session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Context manager for comprehensive tool execution tracing.

    This context manager automatically:
    1. Generates correlation IDs for E2E tracing
    2. Logs structured TRACE_START and TRACE_END messages
    3. Records metrics to Prometheus
    4. Persists execution details to database (async)
    5. Tracks in-progress requests
    6. Captures errors with full context

    Usage:
        with trace_tool_execution(
            tool_name="divide",
            parameters={"a": 10, "b": 2},
            domain="general",
            transport="stdio"
        ) as trace_ctx:
            result = divide(10, 2)
            trace_ctx["output_data"] = result

    Args:
        tool_name: Name of the tool being executed
        parameters: Input parameters passed to the tool
        domain: Domain the tool belongs to (general, kubernetes, etc.)
        transport: Transport protocol (stdio, http, rest)
        correlation_id: Optional correlation ID for distributed tracing
        session_id: Optional session ID for user tracking

    Yields:
        dict: Trace context containing correlation_id, session_id, timing info
    """
    # Generate or use provided IDs
    execution_id = correlation_id or get_correlation_id_from_context() or generate_correlation_id()
    session = session_id or get_session_id_from_context()

    # Calculate request size
    request_size = calculate_payload_size(parameters)

    # Initialize trace context
    context: dict[str, Any] = {
        "correlation_id": execution_id,
        "session_id": session,
        "started_at": datetime.now(UTC),
        "status": "success",  # Optimistic, will be overridden on error
        "request_size_bytes": request_size,
    }

    # Prometheus: Mark execution as started and record request size
    if settings.enable_metrics:
        PROMETHEUS_METRICS.start_tool_execution(tool_name, domain, transport)
        PROMETHEUS_METRICS.record_request_size(tool_name, domain, transport, request_size)

    # High-precision timing for latency measurement
    start_time = time.perf_counter()

    # Structured logging: TRACE_START
    logger.info(
        f"TRACE_START tool={tool_name} domain={domain} transport={transport} "
        f"correlation_id={execution_id} session_id={session or 'none'}"
    )

    try:
        # Execute the tool (yield control back to caller)
        yield context

        # Success path - context remains "success"

    except Exception as e:
        # Error path - capture error details
        context["status"] = "error"
        context["error_type"] = type(e).__name__
        context["error_message"] = str(e)

        logger.error(
            f"TRACE_ERROR tool={tool_name} correlation_id={execution_id} "
            f"error_type={context['error_type']} error_message={context['error_message']}",
            exc_info=True,
        )

        # Re-raise to preserve original exception
        raise

    finally:
        # Calculate execution duration
        duration_seconds = time.perf_counter() - start_time
        context["completed_at"] = datetime.now(UTC)
        context["duration_ms"] = duration_seconds * 1000

        # Calculate response size
        response_size = calculate_payload_size(context.get("output_data"))
        context["response_size_bytes"] = response_size

        # Structured logging: TRACE_END
        logger.info(
            f"TRACE_END tool={tool_name} correlation_id={execution_id} "
            f"duration_ms={context['duration_ms']:.2f} status={context['status']} "
            f"request_bytes={context['request_size_bytes']} response_bytes={response_size}"
        )

        # Prometheus: Record metrics
        if settings.enable_metrics:
            PROMETHEUS_METRICS.record_tool_call(
                tool_name=tool_name,
                domain=domain,
                transport=transport,
                status=context["status"],
                duration_seconds=duration_seconds,
                error_type=context.get("error_type"),
            )
            PROMETHEUS_METRICS.record_response_size(tool_name, domain, transport, response_size)
            PROMETHEUS_METRICS.end_tool_execution(tool_name, domain, transport)

        # Database: Persist execution record (via thread pool, non-blocking)
        # Database writes run in a background thread pool to avoid:
        # 1. Blocking the event loop
        # 2. Event loop mismatch issues with FastMCP's anyio transports
        # The task is fire-and-forget; errors are logged but don't affect tool execution
        _task = asyncio.create_task(
            _persist_execution(tool_name, parameters, context, domain, transport)
        )
        # Suppress "task not awaited" warning - this is intentionally fire-and-forget
        _ = _task

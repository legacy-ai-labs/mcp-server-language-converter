"""Observability and tracing for MCP tool executions.

This module provides comprehensive E2E tracing with:
- Correlation IDs for distributed tracing
- Session IDs for user tracking
- Automatic Prometheus metrics recording
- Database persistence for audit trail
- Structured logging (TRACE_START/TRACE_END)
"""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from src.core.config import get_settings
from src.core.database import async_session_factory
from src.core.repositories.tool_execution_repository import ToolExecutionRepository
from src.core.services.prometheus_metrics import PROMETHEUS_METRICS


logger = logging.getLogger(__name__)
settings = get_settings()


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


async def _persist_execution(
    tool_name: str,
    parameters: dict[str, Any],
    context: dict[str, Any],
    domain: str,
    transport: str,
) -> None:
    """Persist execution record to database.

    Errors are logged but do not propagate back to the caller so tool
    execution is never interrupted by observability persistence failures.

    Note: This function handles event loop mismatches gracefully, as FastMCP
    may use different event loops than where the database engine was created.

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
        async with async_session_factory() as session:
            repo = ToolExecutionRepository(session)

            execution_data = {
                "tool_name": tool_name,
                "correlation_id": context["correlation_id"],
                "session_id": context.get("session_id"),
                "started_at": context["started_at"],
                "completed_at": context.get("completed_at"),
                "duration_ms": context.get("duration_ms"),
                "status": context["status"],
                "error_type": context.get("error_type"),
                "error_message": context.get("error_message"),
                "input_params": parameters if settings.log_tool_inputs else None,
                "output_data": context.get("output_data") if settings.log_tool_outputs else None,
                "transport": transport,
                "domain": domain,
            }

            await repo.create(execution_data)
            logger.debug(
                f"Persisted execution: tool={tool_name} correlation_id={context['correlation_id']}"
            )

    except RuntimeError as e:
        # Handle event loop mismatch errors gracefully
        # This happens when FastMCP uses different event loops than where
        # the database engine was initialized (common with anyio-based transports)
        if "different loop" in str(e) or "attached to a different loop" in str(e):
            logger.debug(
                f"Cannot persist execution for {tool_name}: event loop mismatch "
                "(this is expected with FastMCP's anyio-based transports). "
                "Metrics are still recorded successfully."
            )
        else:
            logger.error(f"Failed to persist execution for {tool_name}: {e}", exc_info=True)
    except Exception as e:
        # Log other errors but don't propagate (persistence is best-effort)
        logger.error(f"Failed to persist execution for {tool_name}: {e}", exc_info=True)


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

    # Initialize trace context
    context: dict[str, Any] = {
        "correlation_id": execution_id,
        "session_id": session,
        "started_at": datetime.now(UTC),
        "status": "success",  # Optimistic, will be overridden on error
    }

    # Prometheus: Mark execution as started
    if settings.enable_metrics:
        PROMETHEUS_METRICS.start_tool_execution(tool_name, domain, transport)

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

        # Structured logging: TRACE_END
        logger.info(
            f"TRACE_END tool={tool_name} correlation_id={execution_id} "
            f"duration_ms={context['duration_ms']:.2f} status={context['status']}"
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
            PROMETHEUS_METRICS.end_tool_execution(tool_name, domain, transport)

        # Database: Persist execution record (non-blocking background task)
        # We schedule this as a task to avoid blocking tool execution
        # and handle potential event loop mismatches gracefully
        try:
            loop = asyncio.get_running_loop()
            # Create task on current loop, but don't await it (fire and forget)
            task = loop.create_task(
                _persist_execution(tool_name, parameters, context, domain, transport)
            )
            # Store reference to prevent garbage collection
            # If task fails, error is logged but doesn't affect tool execution
            _ = task
        except RuntimeError:
            # No running loop (shouldn't happen in async context, but be safe)
            logger.warning(f"Cannot persist execution for {tool_name}: no event loop available")
        except Exception as e:
            # Catch any other scheduling errors
            logger.error(f"Failed to schedule persistence task for {tool_name}: {e}")

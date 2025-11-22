"""FastMCP middleware for automatic observability tracing.

This module provides MCP-native middleware that automatically wraps all tool
executions with comprehensive observability:
- Correlation IDs for E2E tracing
- Prometheus metrics recording
- Database persistence for audit trail
- Structured logging (TRACE_START/TRACE_END)
"""

import logging
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

from src.core.services.common.observability_service import trace_tool_execution


logger = logging.getLogger(__name__)


class ObservabilityMiddleware(Middleware):  # type: ignore[misc]
    """FastMCP middleware for automatic observability tracing of tool executions.

    This middleware intercepts all tool call requests and wraps them with
    comprehensive tracing, metrics, and audit logging.

    The middleware stores domain and transport information in its instance
    so they can be used during tool execution tracing.
    """

    def __init__(self, domain: str, transport: str) -> None:
        """Initialize the observability middleware.

        Args:
            domain: Domain this server handles (e.g., "general", "kubernetes")
            transport: Transport protocol used (e.g., "stdio", "http", "sse")
        """
        super().__init__()
        self.domain = domain
        self.transport = transport
        logger.info(
            f"ObservabilityMiddleware initialized for domain={domain}, transport={transport}"
        )

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        """Hook specifically for tool executions.

        This hook is called for every tool call and wraps execution with
        comprehensive observability tracing.

        Args:
            context: FastMCP middleware context with tool call details
            call_next: Next handler in the middleware chain

        Returns:
            Tool execution result (passed through from next handler)

        Raises:
            Exception: Any exception from tool execution (propagated after tracing)
        """
        # Extract tool information from MCP message
        tool_name = context.message.name if hasattr(context.message, "name") else "unknown"
        tool_arguments = context.message.arguments if hasattr(context.message, "arguments") else {}

        # Get correlation ID from FastMCP context if available
        correlation_id = None
        if context.fastmcp_context:
            correlation_id = context.fastmcp_context.get_state("correlation_id")

        # Wrap execution with observability tracing
        async with trace_tool_execution(
            tool_name=tool_name,
            parameters=tool_arguments,
            domain=self.domain,
            transport=self.transport,
            correlation_id=correlation_id,
        ) as trace_ctx:
            try:
                # Call the next handler (tool execution)
                result = await call_next(context)

                # Record output data for observability
                # FastMCP returns a CallToolResult object, extract content
                if hasattr(result, "content"):
                    # Extract actual content from MCP response
                    trace_ctx["output_data"] = result.content
                else:
                    trace_ctx["output_data"] = result

                return result

            except Exception as e:
                # Error details are automatically captured by trace_tool_execution
                # We just need to re-raise to let MCP handle the error response
                logger.debug(f"Tool {tool_name} raised exception: {type(e).__name__}: {e}")
                raise

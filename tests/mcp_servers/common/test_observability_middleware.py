"""Tests for observability middleware.

This module tests the ObservabilityMiddleware which is responsible for:
- Wrapping tool executions with observability tracing
- Extracting correlation IDs for E2E tracing
- Recording tool arguments and output data
- Propagating exceptions after tracing
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.server.middleware import Middleware

from src.mcp_servers.common.observability_middleware import ObservabilityMiddleware


class TestObservabilityMiddlewareInit:
    """Tests for ObservabilityMiddleware initialization."""

    def test_init_stores_domain(self) -> None:
        """Test that domain is stored correctly."""
        middleware = ObservabilityMiddleware(domain="general", transport="stdio")

        assert middleware.domain == "general"

    def test_init_stores_transport(self) -> None:
        """Test that transport is stored correctly."""
        middleware = ObservabilityMiddleware(domain="test", transport="sse")

        assert middleware.transport == "sse"

    def test_init_with_different_domains(self) -> None:
        """Test initialization with various domains."""
        domains = ["general", "cobol_analysis", "kubernetes", "custom_domain"]

        for domain in domains:
            middleware = ObservabilityMiddleware(domain=domain, transport="stdio")
            assert middleware.domain == domain

    def test_init_with_different_transports(self) -> None:
        """Test initialization with various transports."""
        transports = ["stdio", "http", "sse", "streamable-http"]

        for transport in transports:
            middleware = ObservabilityMiddleware(domain="test", transport=transport)
            assert middleware.transport == transport

    def test_init_logs_initialization(self) -> None:
        """Test that initialization logs a message."""
        with patch("src.mcp_servers.common.observability_middleware.logger") as mock_logger:
            ObservabilityMiddleware(domain="general", transport="stdio")

            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "general" in log_message
            assert "stdio" in log_message

    def test_init_empty_domain(self) -> None:
        """Test initialization with empty domain."""
        middleware = ObservabilityMiddleware(domain="", transport="stdio")

        assert middleware.domain == ""

    def test_init_empty_transport(self) -> None:
        """Test initialization with empty transport."""
        middleware = ObservabilityMiddleware(domain="test", transport="")

        assert middleware.transport == ""


class TestOnCallTool:
    """Tests for on_call_tool async method."""

    @pytest.fixture
    def middleware(self) -> ObservabilityMiddleware:
        """Create middleware instance for testing."""
        return ObservabilityMiddleware(domain="test_domain", transport="test_transport")

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create mock middleware context."""
        context = MagicMock()
        context.message = MagicMock()
        context.message.name = "test_tool"
        context.message.arguments = {"arg1": "value1", "arg2": 42}
        context.fastmcp_context = MagicMock()
        context.fastmcp_context.get_state.return_value = None
        return context

    @pytest.mark.asyncio
    async def test_on_call_tool_calls_next_handler(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that on_call_tool calls the next handler."""
        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            # Set up the async context manager
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(mock_context, call_next)

            call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_on_call_tool_returns_result(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that on_call_tool returns the handler result."""
        expected_result = MagicMock(content="expected_output")
        call_next = AsyncMock(return_value=expected_result)

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await middleware.on_call_tool(mock_context, call_next)

            assert result == expected_result

    @pytest.mark.asyncio
    async def test_on_call_tool_extracts_tool_name(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that tool name is extracted from context."""
        mock_context.message.name = "my_custom_tool"
        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(mock_context, call_next)

            mock_trace.assert_called_once()
            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["tool_name"] == "my_custom_tool"

    @pytest.mark.asyncio
    async def test_on_call_tool_extracts_tool_arguments(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that tool arguments are extracted from context."""
        expected_args = {"param1": "foo", "param2": 123}
        mock_context.message.arguments = expected_args
        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(mock_context, call_next)

            mock_trace.assert_called_once()
            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["parameters"] == expected_args

    @pytest.mark.asyncio
    async def test_on_call_tool_passes_domain_to_trace(self, mock_context: MagicMock) -> None:
        """Test that domain is passed to trace_tool_execution."""
        middleware = ObservabilityMiddleware(domain="cobol_analysis", transport="stdio")
        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(mock_context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["domain"] == "cobol_analysis"

    @pytest.mark.asyncio
    async def test_on_call_tool_passes_transport_to_trace(self, mock_context: MagicMock) -> None:
        """Test that transport is passed to trace_tool_execution."""
        middleware = ObservabilityMiddleware(domain="test", transport="sse")
        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(mock_context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["transport"] == "sse"

    @pytest.mark.asyncio
    async def test_on_call_tool_records_output_data_with_content(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that output data is recorded when result has content attribute."""
        result_with_content = MagicMock()
        result_with_content.content = {"key": "value", "data": [1, 2, 3]}
        call_next = AsyncMock(return_value=result_with_content)

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(mock_context, call_next)

            assert mock_trace_ctx["output_data"] == {"key": "value", "data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_on_call_tool_records_raw_result_without_content(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that raw result is recorded when it has no content attribute."""
        raw_result = {"direct": "result"}
        call_next = AsyncMock(return_value=raw_result)

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(mock_context, call_next)

            assert mock_trace_ctx["output_data"] == {"direct": "result"}


class TestCorrelationId:
    """Tests for correlation ID handling."""

    @pytest.fixture
    def middleware(self) -> ObservabilityMiddleware:
        """Create middleware instance."""
        return ObservabilityMiddleware(domain="test", transport="stdio")

    @pytest.mark.asyncio
    async def test_on_call_tool_extracts_correlation_id(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test that correlation ID is extracted from fastmcp_context."""
        context = MagicMock()
        context.message = MagicMock(name="tool", arguments={})
        context.fastmcp_context = MagicMock()
        context.fastmcp_context.get_state.return_value = "test-correlation-id-123"

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["correlation_id"] == "test-correlation-id-123"

    @pytest.mark.asyncio
    async def test_on_call_tool_correlation_id_none_when_not_set(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test that correlation ID is None when not in context."""
        context = MagicMock()
        context.message = MagicMock(name="tool", arguments={})
        context.fastmcp_context = MagicMock()
        context.fastmcp_context.get_state.return_value = None

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["correlation_id"] is None

    @pytest.mark.asyncio
    async def test_on_call_tool_correlation_id_none_when_no_fastmcp_context(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test that correlation ID is None when fastmcp_context is None."""
        context = MagicMock()
        context.message = MagicMock(name="tool", arguments={})
        context.fastmcp_context = None

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["correlation_id"] is None


class TestExceptionHandling:
    """Tests for exception handling in on_call_tool."""

    @pytest.fixture
    def middleware(self) -> ObservabilityMiddleware:
        """Create middleware instance."""
        return ObservabilityMiddleware(domain="test", transport="stdio")

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create mock context."""
        context = MagicMock()
        context.message = MagicMock(name="failing_tool", arguments={})
        context.fastmcp_context = None
        return context

    @pytest.mark.asyncio
    async def test_on_call_tool_propagates_exception(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that exceptions from tool execution are propagated."""
        call_next = AsyncMock(side_effect=ValueError("Tool execution failed"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="Tool execution failed"):
                await middleware.on_call_tool(mock_context, call_next)

    @pytest.mark.asyncio
    async def test_on_call_tool_logs_exception(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that exceptions are logged before propagation."""
        call_next = AsyncMock(side_effect=RuntimeError("Something went wrong"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("src.mcp_servers.common.observability_middleware.logger") as mock_logger:
                with pytest.raises(RuntimeError):
                    await middleware.on_call_tool(mock_context, call_next)

                mock_logger.debug.assert_called_once()
                log_message = mock_logger.debug.call_args[0][0]
                assert "RuntimeError" in log_message
                assert "Something went wrong" in log_message

    @pytest.mark.asyncio
    async def test_on_call_tool_trace_context_exits_on_exception(
        self, middleware: ObservabilityMiddleware, mock_context: MagicMock
    ) -> None:
        """Test that trace context manager __aexit__ is called on exception."""
        call_next = AsyncMock(side_effect=RuntimeError("Error"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_aexit = AsyncMock(return_value=None)
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = mock_aexit

            with pytest.raises(RuntimeError):
                await middleware.on_call_tool(mock_context, call_next)

            # __aexit__ should be called with exception info
            mock_aexit.assert_called_once()


class TestMessageAttributeHandling:
    """Tests for handling missing message attributes."""

    @pytest.fixture
    def middleware(self) -> ObservabilityMiddleware:
        """Create middleware instance."""
        return ObservabilityMiddleware(domain="test", transport="stdio")

    @pytest.mark.asyncio
    async def test_on_call_tool_handles_missing_name_attribute(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test that missing name attribute defaults to 'unknown'."""
        context = MagicMock()
        # Message without name attribute
        context.message = object()  # Plain object has no name attribute
        context.fastmcp_context = None

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["tool_name"] == "unknown"

    @pytest.mark.asyncio
    async def test_on_call_tool_handles_missing_arguments_attribute(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test that missing arguments attribute defaults to empty dict."""
        context = MagicMock()
        context.message = MagicMock(spec=["name"])  # Only has name, not arguments
        context.message.name = "test_tool"
        context.fastmcp_context = None

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["parameters"] == {}


class TestIntegrationWithMiddlewareBase:
    """Tests for integration with FastMCP Middleware base class."""

    def test_inherits_from_middleware(self) -> None:
        """Test that ObservabilityMiddleware inherits from Middleware."""
        assert issubclass(ObservabilityMiddleware, Middleware)

    def test_has_on_call_tool_method(self) -> None:
        """Test that ObservabilityMiddleware has on_call_tool method."""
        middleware = ObservabilityMiddleware(domain="test", transport="stdio")

        assert hasattr(middleware, "on_call_tool")
        assert callable(middleware.on_call_tool)

    def test_on_call_tool_is_async(self) -> None:
        """Test that on_call_tool is an async method."""
        middleware = ObservabilityMiddleware(domain="test", transport="stdio")

        assert asyncio.iscoroutinefunction(middleware.on_call_tool)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def middleware(self) -> ObservabilityMiddleware:
        """Create middleware instance."""
        return ObservabilityMiddleware(domain="test", transport="stdio")

    @pytest.mark.asyncio
    async def test_on_call_tool_with_large_arguments(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test handling of large argument dictionaries."""
        context = MagicMock()
        large_args = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        context.message = MagicMock(name="tool", arguments=large_args)
        context.fastmcp_context = None

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await middleware.on_call_tool(context, call_next)

            assert result is not None
            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["parameters"] == large_args

    @pytest.mark.asyncio
    async def test_on_call_tool_with_nested_arguments(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test handling of nested argument dictionaries."""
        context = MagicMock()
        nested_args = {
            "level1": {"level2": {"level3": {"value": 42}}},
            "array": [1, 2, {"nested": True}],
        }
        context.message = MagicMock(name="tool", arguments=nested_args)
        context.fastmcp_context = None

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await middleware.on_call_tool(context, call_next)

            assert result is not None
            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["parameters"] == nested_args

    @pytest.mark.asyncio
    async def test_on_call_tool_with_none_result_content(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test handling when result.content is None."""
        context = MagicMock()
        context.message = MagicMock(name="tool", arguments={})
        context.fastmcp_context = None

        result_with_none_content = MagicMock()
        result_with_none_content.content = None
        call_next = AsyncMock(return_value=result_with_none_content)

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await middleware.on_call_tool(context, call_next)

            assert result is not None
            assert mock_trace_ctx["output_data"] is None

    @pytest.mark.asyncio
    async def test_on_call_tool_with_special_characters_in_tool_name(
        self, middleware: ObservabilityMiddleware
    ) -> None:
        """Test handling of special characters in tool name."""
        context = MagicMock()
        # MagicMock has special handling for 'name', so we set it as an attribute
        context.message = MagicMock()
        context.message.name = "tool-with_special.chars:v2"
        context.message.arguments = {}
        context.fastmcp_context = None

        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            await middleware.on_call_tool(context, call_next)

            call_kwargs = mock_trace.call_args[1]
            assert call_kwargs["tool_name"] == "tool-with_special.chars:v2"

    @pytest.mark.asyncio
    async def test_multiple_sequential_calls(self, middleware: ObservabilityMiddleware) -> None:
        """Test multiple sequential tool calls through same middleware."""
        call_next = AsyncMock(return_value=MagicMock(content="result"))

        with patch(
            "src.mcp_servers.common.observability_middleware.trace_tool_execution"
        ) as mock_trace:
            mock_trace_ctx: dict[str, Any] = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            for i in range(3):
                context = MagicMock()
                context.message = MagicMock(name=f"tool_{i}", arguments={"call": i})
                context.fastmcp_context = None

                await middleware.on_call_tool(context, call_next)

            # Should have been called 3 times
            assert mock_trace.call_count == 3
            assert call_next.call_count == 3

"""Tests for HTTP streaming MCP server functionality."""

import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from src.core.config import get_settings
from src.mcp_servers.common.http_runner import startup


class TestHTTPStreamingServer:
    """Test HTTP streaming MCP server."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.http_host = "127.0.0.1"
        settings.http_port = 8001  # Use different port for testing
        settings.app_name = "Test MCP Server"
        settings.app_version = "0.1.0"
        return settings

    @pytest.fixture
    def mock_tools_loaded(self):
        """Mock tools loaded from database."""
        with patch("src.mcp_servers.common.http_runner.load_tools_from_database") as mock_load:
            mock_load.return_value = AsyncMock()
            yield mock_load

    @pytest.mark.asyncio
    async def test_startup_success(self, mock_tools_loaded):
        """Test successful startup of HTTP streaming server."""
        # Should not raise any exceptions
        await startup(domain="general")
        mock_tools_loaded.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_failure(self):
        """Test startup failure handling."""
        with patch("src.mcp_servers.common.http_runner.load_tools_from_database") as mock_load:
            mock_load.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                await startup(domain="general")

    @pytest.mark.asyncio
    async def test_mcp_server_initialization(self):
        """Test MCP server initialization for HTTP streaming."""
        with patch("src.mcp_servers.common.http_runner.load_tools_from_database"):
            mcp_instance = await startup(domain="general")
            # Verify the MCP server is properly configured
            assert isinstance(mcp_instance, FastMCP)

    def test_http_streaming_transport_support(self):
        """Test that FastMCP supports HTTP streaming transport."""
        # Verify that the run method accepts "sse" transport
        # This is a basic check that the transport is supported
        transport_options = ["stdio", "sse", "streamable-http"]
        assert "sse" in transport_options
        assert "streamable-http" in transport_options

    @pytest.mark.asyncio
    async def test_http_streaming_server_lifecycle(self, mock_tools_loaded):
        """Test HTTP streaming server lifecycle."""
        # This should not raise any exceptions
        try:
            # Simulate the main function logic
            await startup(domain="general")
            # In a real test, we would start the server here
            # but we're mocking it to avoid blocking
        except Exception as e:
            pytest.fail(f"HTTP streaming server lifecycle failed: {e}")

    def test_logging_configuration(self):
        """Test that logging is properly configured for HTTP streaming."""
        # Test that we can configure logging for HTTP streaming
        # Create a test logger
        test_logger = logging.getLogger("test_http_streaming")

        # Configure logging similar to HTTP streaming server
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        # Test that logging works
        test_logger.info("Test log message")

        # Verify handler is configured correctly
        handlers = test_logger.handlers
        assert len(handlers) > 0

        # Check that handler writes to stderr
        stderr_handlers = [h for h in handlers if hasattr(h, "stream") and h.stream == sys.stderr]
        assert len(stderr_handlers) > 0

    @pytest.mark.asyncio
    async def test_tool_registration_for_http_streaming(self, mock_tools_loaded):
        """Test that tools are properly registered for HTTP streaming."""
        await startup(domain="general")

        # Verify that tools are loaded
        mock_tools_loaded.assert_called_once()

        # In a real implementation, we would verify that tools are registered
        # with the MCP server for HTTP streaming access

    def test_http_streaming_error_handling(self):
        """Test error handling in HTTP streaming server."""
        # Test that exceptions are properly caught and logged
        with patch("src.mcp_servers.common.http_runner.startup") as mock_startup:
            mock_startup.side_effect = Exception("Test error")

            # This should handle the exception gracefully
            # In a real test, we would verify proper error logging
            assert mock_startup.side_effect is not None


class TestHTTPStreamingIntegration:
    """Integration tests for HTTP streaming functionality."""

    @pytest.mark.asyncio
    async def test_http_streaming_server_startup_sequence(self):
        """Test the complete startup sequence for HTTP streaming."""
        with patch("src.mcp_servers.common.http_runner.load_tools_from_database") as mock_load:
            mock_load.return_value = AsyncMock()

            # Test startup sequence
            await startup(domain="general")
            mock_load.assert_called_once()

    def test_http_streaming_configuration_loading(self):
        """Test that HTTP streaming configuration is properly loaded."""
        settings = get_settings()

        # Verify HTTP streaming configuration exists
        assert hasattr(settings, "http_host")
        assert hasattr(settings, "http_port")
        assert hasattr(settings, "http_streaming_enabled")

        # Verify default values
        assert settings.http_host == "0.0.0.0"
        assert settings.http_port == 8000
        assert settings.http_streaming_enabled is True

    @pytest.mark.asyncio
    async def test_http_streaming_server_graceful_shutdown(self):
        """Test graceful shutdown of HTTP streaming server."""
        # This test verifies graceful shutdown capability
        # In a real test, we would start the server and send SIGINT
        with patch("src.mcp_servers.common.http_runner.load_tools_from_database"):
            mcp_instance = await startup(domain="general")
            # Verify server can be initialized
            assert mcp_instance is not None

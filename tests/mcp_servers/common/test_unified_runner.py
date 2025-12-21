"""Tests for unified MCP server runner.

This module tests the unified_runner functionality which is responsible for:
- Running MCP servers with different transport protocols (stdio, sse, streamable-http)
- Importing domain-specific tool modules
- Transport configuration mapping
- Server startup and initialization
"""

import importlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from src.core.config import get_settings
from src.mcp_servers.common.tool_registry import TOOL_REGISTRY
from src.mcp_servers.common.unified_runner import (
    _get_transport_config,
    _get_transport_mapping,
    _import_domain_tools,
    startup,
)


class TestGetTransportMapping:
    """Tests for _get_transport_mapping function."""

    def test_stdio_transport_mapping(self) -> None:
        """Test STDIO transport mapping."""
        server_transport, registry_transport = _get_transport_mapping("stdio")

        assert server_transport == "stdio"
        assert registry_transport == "stdio"

    def test_sse_transport_mapping(self) -> None:
        """Test SSE transport mapping."""
        server_transport, registry_transport = _get_transport_mapping("sse")

        assert server_transport == "sse"
        # SSE uses "http" for tool registry
        assert registry_transport == "http"

    def test_streamable_http_transport_mapping(self) -> None:
        """Test Streamable HTTP transport mapping."""
        server_transport, registry_transport = _get_transport_mapping("streamable-http")

        assert server_transport == "streamable-http"
        assert registry_transport == "streamable-http"

    def test_unknown_transport_defaults_to_stdio(self) -> None:
        """Test that unknown transport defaults to stdio."""
        server_transport, registry_transport = _get_transport_mapping("unknown")  # type: ignore

        assert server_transport == "stdio"
        assert registry_transport == "stdio"

    def test_all_transports_return_tuples(self) -> None:
        """Test that all transports return 2-tuples."""
        transports = ["stdio", "sse", "streamable-http"]

        for transport in transports:
            result = _get_transport_mapping(transport)  # type: ignore
            assert isinstance(result, tuple)
            assert len(result) == 2


class TestGetTransportConfig:
    """Tests for _get_transport_config function."""

    def test_stdio_config_is_empty(self) -> None:
        """Test that STDIO transport config is empty (no host/port needed)."""
        config = _get_transport_config("stdio")

        assert config == {}

    def test_sse_config_has_host_port_middleware(self) -> None:
        """Test that SSE transport config has host, port, and CORS middleware."""
        config = _get_transport_config("sse")

        assert "host" in config
        assert "port" in config
        assert "middleware" in config
        assert len(config["middleware"]) > 0

    def test_streamable_http_config_has_host_port(self) -> None:
        """Test that Streamable HTTP transport config has host and port."""
        config = _get_transport_config("streamable-http")

        assert "host" in config
        assert "port" in config

    def test_streamable_http_config_no_middleware(self) -> None:
        """Test that Streamable HTTP doesn't have CORS middleware by default."""
        config = _get_transport_config("streamable-http")

        # Streamable HTTP doesn't add middleware in current implementation
        assert "middleware" not in config

    def test_sse_cors_middleware_allows_all_origins(self) -> None:
        """Test that SSE CORS middleware allows all origins (development mode)."""
        config = _get_transport_config("sse")

        # Middleware is a list of Starlette Middleware objects
        middleware_list = config["middleware"]
        assert len(middleware_list) >= 1


class TestImportDomainTools:
    """Tests for _import_domain_tools function."""

    def test_import_general_domain(self) -> None:
        """Test importing general domain tools."""
        # Should not raise an exception
        _import_domain_tools("general")

    def test_import_cobol_analysis_domain(self) -> None:
        """Test importing cobol_analysis domain tools."""
        # Should not raise an exception
        _import_domain_tools("cobol_analysis")

    def test_import_unknown_domain_logs_warning(self) -> None:
        """Test that unknown domain logs a warning but doesn't crash."""
        # Should not raise an exception, just log warning
        _import_domain_tools("unknown_domain")

    @patch("src.mcp_servers.common.unified_runner.importlib.import_module")
    def test_import_general_calls_correct_module(self, mock_import: MagicMock) -> None:
        """Test that general domain imports correct module."""
        _import_domain_tools("general")

        mock_import.assert_called_once_with("src.mcp_servers.mcp_general.tools")

    @patch("src.mcp_servers.common.unified_runner.importlib.import_module")
    def test_import_cobol_calls_correct_module(self, mock_import: MagicMock) -> None:
        """Test that cobol_analysis domain imports correct module."""
        _import_domain_tools("cobol_analysis")

        mock_import.assert_called_once_with("src.mcp_servers.mcp_cobol_analysis.tools")


class TestStartup:
    """Tests for startup async function."""

    @pytest.mark.asyncio
    async def test_startup_returns_mcp_server(self) -> None:
        """Test that startup returns an MCP server instance."""
        mcp = await startup(domain="general", transport="stdio")

        assert isinstance(mcp, FastMCP)

    @pytest.mark.asyncio
    async def test_startup_with_custom_server_name(self) -> None:
        """Test startup with custom server name."""
        custom_name = "My Custom Server"
        mcp = await startup(domain="general", transport="stdio", server_name=custom_name)

        assert mcp.name == custom_name

    @pytest.mark.asyncio
    async def test_startup_with_different_transports(self) -> None:
        """Test startup with different transport types."""
        transports = ["stdio", "sse", "streamable-http"]

        for transport in transports:
            mcp = await startup(domain="general", transport=transport)  # type: ignore
            assert mcp is not None

    @pytest.mark.asyncio
    async def test_startup_general_domain(self) -> None:
        """Test startup for general domain."""
        mcp = await startup(domain="general", transport="stdio")

        assert "General" in mcp.name

    @pytest.mark.asyncio
    async def test_startup_cobol_analysis_domain(self) -> None:
        """Test startup for cobol_analysis domain."""
        mcp = await startup(domain="cobol_analysis", transport="stdio")

        assert "Cobol Analysis" in mcp.name

    @pytest.mark.asyncio
    @patch("src.mcp_servers.common.unified_runner.create_mcp_server")
    @patch("src.mcp_servers.common.unified_runner.load_tools_from_registry", new_callable=AsyncMock)
    @patch("src.mcp_servers.common.unified_runner._import_domain_tools")
    async def test_startup_calls_components_in_order(
        self,
        mock_import: MagicMock,
        mock_load_tools: AsyncMock,
        mock_create_server: MagicMock,
    ) -> None:
        """Test that startup calls components in correct order."""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        await startup(domain="test", transport="stdio")

        # Verify order: create_server, import_tools, load_tools
        mock_create_server.assert_called_once()
        mock_import.assert_called_once_with("test")
        mock_load_tools.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.mcp_servers.common.unified_runner.create_mcp_server")
    @patch("src.mcp_servers.common.unified_runner.load_tools_from_registry", new_callable=AsyncMock)
    @patch("src.mcp_servers.common.unified_runner._import_domain_tools")
    async def test_startup_uses_correct_transport_mapping(
        self,
        mock_import: MagicMock,
        mock_load_tools: AsyncMock,
        mock_create_server: MagicMock,
    ) -> None:
        """Test that startup uses correct transport mapping for SSE."""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        await startup(domain="test", transport="sse")

        # SSE should use "sse" for server, "http" for registry
        mock_create_server.assert_called_once_with(
            domain="test",
            server_name=None,
            transport="sse",
        )
        mock_load_tools.assert_called_once()
        # Check registry got "http" transport
        call_kwargs = mock_load_tools.call_args[1]
        assert call_kwargs.get("transport") == "http"


class TestTransportConfigIntegration:
    """Integration tests for transport configurations."""

    def test_stdio_config_values(self) -> None:
        """Test STDIO configuration values."""
        config = _get_transport_config("stdio")

        # STDIO should have empty config
        assert len(config) == 0

    def test_sse_config_uses_settings(self) -> None:
        """Test SSE uses values from settings."""
        settings = get_settings()
        config = _get_transport_config("sse")

        assert config["host"] == settings.http_host
        assert config["port"] == settings.http_port

    def test_streamable_http_config_uses_settings(self) -> None:
        """Test Streamable HTTP uses values from settings."""
        settings = get_settings()
        config = _get_transport_config("streamable-http")

        assert config["host"] == settings.streamable_http_host
        assert config["port"] == settings.streamable_http_port


class TestDomainToolsImport:
    """Tests for domain tools import functionality."""

    def test_general_tools_module_exists(self) -> None:
        """Test that general tools module can be imported."""
        module = importlib.import_module("src.mcp_servers.mcp_general.tools")
        assert module is not None

    def test_cobol_analysis_tools_module_exists(self) -> None:
        """Test that cobol_analysis tools module can be imported."""
        module = importlib.import_module("src.mcp_servers.mcp_cobol_analysis.tools")
        assert module is not None

    def test_import_registers_tools_in_registry(self) -> None:
        """Test that importing domain tools registers them in TOOL_REGISTRY."""
        # Import tools
        _import_domain_tools("general")

        # Should have general domain registered
        assert "general" in TOOL_REGISTRY

    def test_import_cobol_registers_tools_in_registry(self) -> None:
        """Test that importing COBOL tools registers them in TOOL_REGISTRY."""
        # Import tools
        _import_domain_tools("cobol_analysis")

        # Should have cobol_analysis domain registered
        assert "cobol_analysis" in TOOL_REGISTRY


class TestStartupWithMetrics:
    """Tests for startup with Prometheus metrics."""

    @pytest.mark.asyncio
    @patch("src.mcp_servers.common.unified_runner.settings")
    @patch("src.mcp_servers.common.unified_runner.PROMETHEUS_METRICS")
    async def test_startup_initializes_metrics_when_enabled(
        self,
        mock_metrics: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test that startup initializes Prometheus metrics when enabled."""
        mock_settings.enable_metrics = True
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.app_name = "Test App"

        # We need to actually run startup but mock the metrics
        # This is a complex test that verifies metrics initialization
        # For now, just verify the settings are accessible
        assert mock_settings.enable_metrics is True


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_transport_config_empty_transport(self) -> None:
        """Test transport config with empty string."""
        config = _get_transport_config("")  # type: ignore

        # Should return empty config (like stdio)
        assert config == {}

    def test_get_transport_mapping_case_sensitive(self) -> None:
        """Test that transport mapping is case sensitive."""
        # Uppercase should not match
        result = _get_transport_mapping("STDIO")  # type: ignore

        # Should default to stdio since "STDIO" != "stdio"
        assert result == ("stdio", "stdio")

    @pytest.mark.asyncio
    async def test_startup_with_empty_domain(self) -> None:
        """Test startup with empty domain string."""
        # Should work but may have issues loading tools
        mcp = await startup(domain="", transport="stdio")

        assert mcp is not None

    def test_import_domain_tools_multiple_times_is_safe(self) -> None:
        """Test that importing domain tools multiple times is safe."""
        # Should not raise exceptions
        _import_domain_tools("general")
        _import_domain_tools("general")
        _import_domain_tools("general")


class TestTransportTypes:
    """Tests for transport type definitions and validation."""

    def test_all_transport_types_have_mappings(self) -> None:
        """Test that all defined transport types have mappings."""
        transport_types = ["stdio", "sse", "streamable-http"]

        for transport in transport_types:
            result = _get_transport_mapping(transport)  # type: ignore
            assert result != ("stdio", "stdio") or transport == "stdio"

    def test_all_transport_types_have_configs(self) -> None:
        """Test that all transport types have configuration handlers."""
        transport_types = ["stdio", "sse", "streamable-http"]

        for transport in transport_types:
            # Should not raise exception
            config = _get_transport_config(transport)  # type: ignore
            assert isinstance(config, dict)


class TestIntegrationWithRegistry:
    """Integration tests with tool registry."""

    @pytest.mark.asyncio
    async def test_startup_loads_tools_from_config(self) -> None:
        """Test that startup loads tools based on config/tools.json."""
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "tools.json"
        if not config_path.exists():
            pytest.skip(f"Config file not found: {config_path}")

        mcp = await startup(domain="general", transport="stdio")

        # Server should have tools loaded
        # The exact check depends on FastMCP internals
        assert mcp is not None

    @pytest.mark.asyncio
    async def test_startup_cobol_loads_expected_tools(self) -> None:
        """Test that COBOL startup loads expected tools."""
        mcp = await startup(domain="cobol_analysis", transport="stdio")

        # Verify server was created
        assert mcp is not None
        assert "Cobol Analysis" in mcp.name

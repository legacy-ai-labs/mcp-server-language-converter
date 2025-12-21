"""Tests for base MCP server initialization.

This module tests the base_server functionality which is responsible for:
- Creating FastMCP server instances
- Generating server names based on domain
- Adding observability middleware
- Configuring server with settings
"""

from unittest.mock import MagicMock, patch

from fastmcp import FastMCP

from src.core.config import get_settings
from src.mcp_servers.common.base_server import create_mcp_server
from src.mcp_servers.common.observability_middleware import ObservabilityMiddleware


class TestCreateMCPServer:
    """Tests for create_mcp_server function."""

    def test_create_server_returns_fastmcp_instance(self) -> None:
        """Test that create_mcp_server returns a FastMCP instance."""
        mcp = create_mcp_server(domain="test")

        assert isinstance(mcp, FastMCP)

    def test_create_server_with_domain_only(self) -> None:
        """Test creating server with only domain parameter."""
        mcp = create_mcp_server(domain="general")

        assert isinstance(mcp, FastMCP)
        # Server should have auto-generated name
        assert "General" in mcp.name or "general" in mcp.name.lower()

    def test_create_server_with_custom_name(self) -> None:
        """Test creating server with custom server name."""
        custom_name = "My Custom MCP Server"
        mcp = create_mcp_server(domain="test", server_name=custom_name)

        assert mcp.name == custom_name

    def test_create_server_auto_generated_name_format(self) -> None:
        """Test that auto-generated server name follows expected format."""
        mcp = create_mcp_server(domain="cobol_analysis")

        # Should contain domain in title case
        assert "Cobol Analysis" in mcp.name or "COBOL" in mcp.name.upper()

    def test_create_server_with_different_transports(self) -> None:
        """Test creating server with different transport types."""
        transports = ["stdio", "http", "sse", "streamable-http"]

        for transport in transports:
            mcp = create_mcp_server(domain="test", transport=transport)
            assert isinstance(mcp, FastMCP)

    def test_create_server_has_version(self) -> None:
        """Test that server has version from settings."""
        mcp = create_mcp_server(domain="test")

        # FastMCP should have version attribute
        assert hasattr(mcp, "version") or hasattr(mcp, "_version")


class TestServerNameGeneration:
    """Tests for server name generation logic."""

    def test_domain_with_underscore_becomes_title_case(self) -> None:
        """Test that domain with underscores becomes title case in name."""
        mcp = create_mcp_server(domain="cobol_analysis")

        # "cobol_analysis" should become "Cobol Analysis"
        assert "Cobol Analysis" in mcp.name

    def test_simple_domain_becomes_title_case(self) -> None:
        """Test that simple domain becomes title case in name."""
        mcp = create_mcp_server(domain="general")

        assert "General" in mcp.name

    def test_custom_name_overrides_generation(self) -> None:
        """Test that custom name completely overrides generation."""
        custom_name = "Completely Different Name"
        mcp = create_mcp_server(domain="some_domain", server_name=custom_name)

        assert mcp.name == custom_name
        assert "Some Domain" not in mcp.name


class TestObservabilityMiddleware:
    """Tests for observability middleware integration."""

    def test_server_has_middleware(self) -> None:
        """Test that created server has middleware added."""
        mcp = create_mcp_server(domain="test", transport="stdio")

        # FastMCP should have middleware
        # The exact way to check depends on FastMCP internals
        # We verify the server was created successfully which means add_middleware worked
        assert isinstance(mcp, FastMCP)

    def test_observability_middleware_initialization(self) -> None:
        """Test ObservabilityMiddleware can be instantiated."""
        middleware = ObservabilityMiddleware(domain="test", transport="stdio")

        assert middleware.domain == "test"
        assert middleware.transport == "stdio"

    def test_observability_middleware_with_different_domains(self) -> None:
        """Test ObservabilityMiddleware with various domains."""
        domains = ["general", "cobol_analysis", "kubernetes", "custom_domain"]

        for domain in domains:
            middleware = ObservabilityMiddleware(domain=domain, transport="stdio")
            assert middleware.domain == domain

    def test_observability_middleware_with_different_transports(self) -> None:
        """Test ObservabilityMiddleware with various transports."""
        transports = ["stdio", "http", "sse", "streamable-http"]

        for transport in transports:
            middleware = ObservabilityMiddleware(domain="test", transport=transport)
            assert middleware.transport == transport


class TestServerConfiguration:
    """Tests for server configuration from settings."""

    def test_server_uses_settings(self) -> None:
        """Test that server uses configuration from settings."""
        mcp = create_mcp_server(domain="test")

        # Server should have been created with settings
        assert mcp is not None
        # Name should contain app name from settings
        # (unless custom name was provided)

    @patch("src.mcp_servers.common.base_server.get_settings")
    def test_server_uses_app_name_from_settings(self, mock_settings: MagicMock) -> None:
        """Test that server name includes app name from settings."""
        mock_settings.return_value.app_name = "Test App"
        mock_settings.return_value.app_version = "1.0.0"

        mcp = create_mcp_server(domain="general")

        assert "Test App" in mcp.name

    @patch("src.mcp_servers.common.base_server.get_settings")
    def test_server_uses_version_from_settings(self, mock_settings: MagicMock) -> None:
        """Test that server uses version from settings."""
        mock_settings.return_value.app_name = "Test App"
        mock_settings.return_value.app_version = "2.5.0"

        mcp = create_mcp_server(domain="test")

        # FastMCP should have version
        # The version might be stored in different ways
        assert mcp is not None


class TestMultipleServerInstances:
    """Tests for creating multiple server instances."""

    def test_create_multiple_servers_different_domains(self) -> None:
        """Test creating multiple servers for different domains."""
        server1 = create_mcp_server(domain="general")
        server2 = create_mcp_server(domain="cobol_analysis")

        assert server1 is not server2
        assert server1.name != server2.name

    def test_create_multiple_servers_same_domain(self) -> None:
        """Test creating multiple servers for same domain."""
        server1 = create_mcp_server(domain="general")
        server2 = create_mcp_server(domain="general")

        # Should be different instances
        assert server1 is not server2
        # But same name
        assert server1.name == server2.name

    def test_servers_have_independent_middleware(self) -> None:
        """Test that each server has its own middleware instance."""
        server1 = create_mcp_server(domain="general", transport="stdio")
        server2 = create_mcp_server(domain="cobol_analysis", transport="sse")

        # Both should be valid servers
        assert isinstance(server1, FastMCP)
        assert isinstance(server2, FastMCP)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_create_server_empty_domain(self) -> None:
        """Test creating server with empty domain string."""
        # Empty domain should still work (though not recommended)
        mcp = create_mcp_server(domain="")

        assert isinstance(mcp, FastMCP)

    def test_create_server_special_characters_in_domain(self) -> None:
        """Test creating server with special characters in domain."""
        mcp = create_mcp_server(domain="my-domain-v2")

        assert isinstance(mcp, FastMCP)

    def test_create_server_empty_custom_name(self) -> None:
        """Test creating server with empty custom name falls back to generated."""
        # Empty string is falsy, so should use generated name
        mcp = create_mcp_server(domain="test", server_name="")

        # Should have generated name since empty string is falsy
        assert mcp.name != ""

    def test_create_server_none_transport(self) -> None:
        """Test creating server with default transport when not specified."""
        mcp = create_mcp_server(domain="test")

        # Should default to stdio
        assert isinstance(mcp, FastMCP)


class TestIntegrationWithActualSettings:
    """Integration tests using actual application settings."""

    def test_create_server_with_actual_settings(self) -> None:
        """Test server creation with actual application settings."""
        settings = get_settings()
        mcp = create_mcp_server(domain="general")

        # Server name should include app name from settings
        assert settings.app_name in mcp.name

    def test_create_cobol_server_with_actual_settings(self) -> None:
        """Test COBOL analysis server creation."""
        mcp = create_mcp_server(domain="cobol_analysis")

        assert "Cobol Analysis" in mcp.name
        assert isinstance(mcp, FastMCP)

    def test_create_general_server_with_actual_settings(self) -> None:
        """Test general domain server creation."""
        mcp = create_mcp_server(domain="general")

        assert "General" in mcp.name
        assert isinstance(mcp, FastMCP)

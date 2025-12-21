"""Tests for tool registry.

This module tests the tool_registry functionality which is responsible for:
- Decorator-based tool registration in a global registry
- Loading tools from registry and registering with FastMCP
- Filtering tools based on JSON configuration
- Maintaining compatibility between code and config
"""

import json
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.mcp_servers.common.tool_registry import (
    TOOL_REGISTRY,
    load_tools_from_registry,
    register_tool,
)


class TestRegisterToolDecorator:
    """Tests for register_tool decorator factory."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        TOOL_REGISTRY.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        TOOL_REGISTRY.clear()

    def test_register_tool_adds_to_registry(self) -> None:
        """Test that register_tool adds function to registry."""

        @register_tool(domain="test_domain", tool_name="my_tool")
        def my_tool_func() -> str:
            return "result"

        assert "test_domain" in TOOL_REGISTRY
        assert len(TOOL_REGISTRY["test_domain"]) == 1

    def test_register_tool_preserves_function(self) -> None:
        """Test that register_tool returns the original function."""

        @register_tool(domain="test_domain", tool_name="my_tool")
        def my_tool_func() -> str:
            return "result"

        assert my_tool_func() == "result"

    def test_register_tool_stores_tool_name(self) -> None:
        """Test that tool name is stored correctly."""

        @register_tool(domain="test_domain", tool_name="custom_name")
        def my_func() -> None:
            pass

        tool_name, _, _ = TOOL_REGISTRY["test_domain"][0]
        assert tool_name == "custom_name"

    def test_register_tool_stores_description(self) -> None:
        """Test that description is stored correctly."""

        @register_tool(
            domain="test_domain",
            tool_name="my_tool",
            description="This is my tool description",
        )
        def my_func() -> None:
            pass

        _, _, description = TOOL_REGISTRY["test_domain"][0]
        assert description == "This is my tool description"

    def test_register_tool_empty_description_default(self) -> None:
        """Test that description defaults to empty string."""

        @register_tool(domain="test_domain", tool_name="my_tool")
        def my_func() -> None:
            pass

        _, _, description = TOOL_REGISTRY["test_domain"][0]
        assert description == ""

    def test_register_tool_stores_function_reference(self) -> None:
        """Test that function reference is stored correctly."""

        @register_tool(domain="test_domain", tool_name="my_tool")
        def my_func() -> str:
            return "test"

        _, stored_func, _ = TOOL_REGISTRY["test_domain"][0]
        assert stored_func is my_func

    def test_register_multiple_tools_same_domain(self) -> None:
        """Test registering multiple tools in the same domain."""

        @register_tool(domain="test_domain", tool_name="tool1")
        def tool1() -> None:
            pass

        @register_tool(domain="test_domain", tool_name="tool2")
        def tool2() -> None:
            pass

        @register_tool(domain="test_domain", tool_name="tool3")
        def tool3() -> None:
            pass

        assert len(TOOL_REGISTRY["test_domain"]) == 3
        tool_names = [name for name, _, _ in TOOL_REGISTRY["test_domain"]]
        assert tool_names == ["tool1", "tool2", "tool3"]

    def test_register_tools_different_domains(self) -> None:
        """Test registering tools in different domains."""

        @register_tool(domain="domain_a", tool_name="tool_a")
        def tool_a() -> None:
            pass

        @register_tool(domain="domain_b", tool_name="tool_b")
        def tool_b() -> None:
            pass

        assert "domain_a" in TOOL_REGISTRY
        assert "domain_b" in TOOL_REGISTRY
        assert len(TOOL_REGISTRY["domain_a"]) == 1
        assert len(TOOL_REGISTRY["domain_b"]) == 1

    def test_register_async_function(self) -> None:
        """Test registering an async function."""

        @register_tool(domain="test_domain", tool_name="async_tool")
        async def async_tool() -> str:
            return "async result"

        assert "test_domain" in TOOL_REGISTRY
        _, stored_func, _ = TOOL_REGISTRY["test_domain"][0]
        assert stored_func is async_tool

    def test_register_tool_logs_debug_message(self) -> None:
        """Test that registration logs a debug message."""
        with patch("src.mcp_servers.common.tool_registry.logger") as mock_logger:

            @register_tool(domain="test_domain", tool_name="logged_tool")
            def logged_tool() -> None:
                pass

            mock_logger.debug.assert_called_once()
            log_message = mock_logger.debug.call_args[0][0]
            assert "logged_tool" in log_message
            assert "test_domain" in log_message


class TestLoadToolsFromRegistry:
    """Tests for load_tools_from_registry function."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        TOOL_REGISTRY.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        TOOL_REGISTRY.clear()

    @pytest.fixture
    def mock_mcp(self) -> MagicMock:
        """Create mock FastMCP instance."""
        mcp = MagicMock()
        mcp.tool = MagicMock(return_value=lambda f: f)
        return mcp

    @pytest.fixture
    def temp_config_file(self) -> Iterator[str]:
        """Create a temporary config file for testing."""
        config_data = {
            "version": "1.0",
            "description": "Test config",
            "domains": {
                "test_domain": {
                    "tools": [
                        {
                            "name": "active_tool",
                            "description": "Active tool from config",
                            "handler_name": "active_tool_handler",
                            "category": "testing",
                            "is_active": True,
                        },
                        {
                            "name": "inactive_tool",
                            "description": "Inactive tool",
                            "handler_name": "inactive_tool_handler",
                            "category": "testing",
                            "is_active": False,
                        },
                    ]
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        yield temp_path
        Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_load_tools_no_registered_tools(self, mock_mcp: MagicMock) -> None:
        """Test loading when no tools are registered for domain."""
        with patch("src.mcp_servers.common.tool_registry.logger") as mock_logger:
            await load_tools_from_registry(mock_mcp, domain="nonexistent")

            mock_logger.warning.assert_called_once()
            assert "No tools registered" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_load_tools_registers_active_tools(
        self, mock_mcp: MagicMock, temp_config_file: str
    ) -> None:
        """Test that active tools are registered with FastMCP."""

        @register_tool(domain="test_domain", tool_name="active_tool")
        async def active_tool() -> str:
            return "active"

        await load_tools_from_registry(mock_mcp, domain="test_domain", config_path=temp_config_file)

        # Should have called mcp.tool() once for the active tool
        mock_mcp.tool.assert_called()

    @pytest.mark.asyncio
    async def test_load_tools_skips_inactive_tools(
        self, mock_mcp: MagicMock, temp_config_file: str
    ) -> None:
        """Test that inactive tools are not registered."""

        @register_tool(domain="test_domain", tool_name="inactive_tool")
        async def inactive_tool() -> str:
            return "inactive"

        with patch("src.mcp_servers.common.tool_registry.logger") as mock_logger:
            await load_tools_from_registry(
                mock_mcp, domain="test_domain", config_path=temp_config_file
            )

            # Should log that it's skipping the inactive tool
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any("inactive_tool" in call and "not active" in call for call in debug_calls)

    @pytest.mark.asyncio
    async def test_load_tools_uses_config_description(
        self, mock_mcp: MagicMock, temp_config_file: str
    ) -> None:
        """Test that description from config takes precedence."""

        @register_tool(
            domain="test_domain",
            tool_name="active_tool",
            description="Code description",
        )
        async def active_tool() -> str:
            return "active"

        await load_tools_from_registry(mock_mcp, domain="test_domain", config_path=temp_config_file)

        # Should use config description "Active tool from config"
        mock_mcp.tool.assert_called()
        call_kwargs = mock_mcp.tool.call_args[1]
        assert call_kwargs["description"] == "Active tool from config"

    @pytest.mark.asyncio
    async def test_load_tools_warns_missing_registered_tools(self, mock_mcp: MagicMock) -> None:
        """Test warning when tools in config are not registered in code."""
        config_data = {
            "version": "1.0",
            "domains": {
                "test_domain": {
                    "tools": [
                        {
                            "name": "unregistered_tool",
                            "description": "Not in code",
                            "handler_name": "handler",
                            "category": "test",
                            "is_active": True,
                        }
                    ]
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            # Register a different tool
            @register_tool(domain="test_domain", tool_name="other_tool")
            async def other_tool() -> str:
                return "other"

            with patch("src.mcp_servers.common.tool_registry.logger") as mock_logger:
                await load_tools_from_registry(
                    mock_mcp, domain="test_domain", config_path=temp_path
                )

                # Should warn about unregistered_tool
                warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                assert any("unregistered_tool" in call for call in warning_calls)
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_load_tools_stores_dynamic_tools(
        self, mock_mcp: MagicMock, temp_config_file: str
    ) -> None:
        """Test that dynamic tools are stored to prevent garbage collection."""

        @register_tool(domain="test_domain", tool_name="active_tool")
        async def active_tool() -> str:
            return "active"

        await load_tools_from_registry(mock_mcp, domain="test_domain", config_path=temp_config_file)

        # Should have _dynamic_tools attribute
        assert hasattr(mock_mcp, "_dynamic_tools")

    @pytest.mark.asyncio
    async def test_load_tools_logs_info_messages(
        self, mock_mcp: MagicMock, temp_config_file: str
    ) -> None:
        """Test that loading logs appropriate info messages."""

        @register_tool(domain="test_domain", tool_name="active_tool")
        async def active_tool() -> str:
            return "active"

        with patch("src.mcp_servers.common.tool_registry.logger") as mock_logger:
            await load_tools_from_registry(
                mock_mcp, domain="test_domain", config_path=temp_config_file
            )

            # Should log info about loading
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Loading" in call for call in info_calls)
            assert any("Successfully registered" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_load_tools_handles_exception(self, mock_mcp: MagicMock) -> None:
        """Test that exceptions during loading are handled and re-raised."""

        @register_tool(domain="test_domain", tool_name="tool")
        async def tool() -> str:
            return "test"

        with (
            patch(
                "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
                side_effect=RuntimeError("Config error"),
            ),
            pytest.raises(RuntimeError, match="Config error"),
        ):
            await load_tools_from_registry(mock_mcp, domain="test_domain")

    @pytest.mark.asyncio
    async def test_load_tools_multiple_active_tools(self, mock_mcp: MagicMock) -> None:
        """Test loading multiple active tools."""
        config_data = {
            "version": "1.0",
            "domains": {
                "test_domain": {
                    "tools": [
                        {
                            "name": "tool1",
                            "description": "Tool 1",
                            "handler_name": "h1",
                            "category": "test",
                            "is_active": True,
                        },
                        {
                            "name": "tool2",
                            "description": "Tool 2",
                            "handler_name": "h2",
                            "category": "test",
                            "is_active": True,
                        },
                        {
                            "name": "tool3",
                            "description": "Tool 3",
                            "handler_name": "h3",
                            "category": "test",
                            "is_active": True,
                        },
                    ]
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:

            @register_tool(domain="test_domain", tool_name="tool1")
            async def tool1() -> str:
                return "1"

            @register_tool(domain="test_domain", tool_name="tool2")
            async def tool2() -> str:
                return "2"

            @register_tool(domain="test_domain", tool_name="tool3")
            async def tool3() -> str:
                return "3"

            await load_tools_from_registry(mock_mcp, domain="test_domain", config_path=temp_path)

            # Should have called mcp.tool() 3 times
            assert mock_mcp.tool.call_count == 3
        finally:
            Path(temp_path).unlink()


class TestToolRegistryGlobalState:
    """Tests for TOOL_REGISTRY global state."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        TOOL_REGISTRY.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        TOOL_REGISTRY.clear()

    def test_registry_starts_empty(self) -> None:
        """Test that registry is empty at start."""
        # Already cleared in setup
        assert len(TOOL_REGISTRY) == 0

    def test_registry_persists_across_registrations(self) -> None:
        """Test that registry persists tools across registrations."""

        @register_tool(domain="domain1", tool_name="tool1")
        def tool1() -> None:
            pass

        assert len(TOOL_REGISTRY) == 1

        @register_tool(domain="domain2", tool_name="tool2")
        def tool2() -> None:
            pass

        assert len(TOOL_REGISTRY) == 2
        assert "domain1" in TOOL_REGISTRY
        assert "domain2" in TOOL_REGISTRY

    def test_registry_is_dict_type(self) -> None:
        """Test that registry is a dictionary."""
        assert isinstance(TOOL_REGISTRY, dict)

    def test_registry_values_are_lists(self) -> None:
        """Test that registry values are lists of tuples."""

        @register_tool(domain="test", tool_name="tool")
        def tool() -> None:
            pass

        assert isinstance(TOOL_REGISTRY["test"], list)
        assert isinstance(TOOL_REGISTRY["test"][0], tuple)
        assert len(TOOL_REGISTRY["test"][0]) == 3  # (name, func, description)


class TestDecoratorChaining:
    """Tests for decorator chaining with @mcp.tool()."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        TOOL_REGISTRY.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        TOOL_REGISTRY.clear()

    def test_register_tool_works_with_other_decorators(self) -> None:
        """Test that register_tool works when chained with other decorators."""

        def other_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            func._decorated = True  # type: ignore
            return func

        @register_tool(domain="test", tool_name="chained_tool")
        @other_decorator
        def chained_tool() -> str:
            return "chained"

        assert "test" in TOOL_REGISTRY
        _, stored_func, _ = TOOL_REGISTRY["test"][0]
        assert hasattr(stored_func, "_decorated")
        assert stored_func._decorated is True

    def test_register_tool_preserves_function_metadata(self) -> None:
        """Test that register_tool preserves function name and docstring."""

        @register_tool(domain="test", tool_name="documented_tool")
        def documented_tool() -> str:
            """This is a docstring."""
            return "documented"

        assert documented_tool.__name__ == "documented_tool"
        assert documented_tool.__doc__ == "This is a docstring."


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        TOOL_REGISTRY.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        TOOL_REGISTRY.clear()

    def test_register_tool_empty_domain(self) -> None:
        """Test registering with empty domain string."""

        @register_tool(domain="", tool_name="tool")
        def tool() -> None:
            pass

        assert "" in TOOL_REGISTRY

    def test_register_tool_empty_tool_name(self) -> None:
        """Test registering with empty tool name."""

        @register_tool(domain="test", tool_name="")
        def tool() -> None:
            pass

        tool_name, _, _ = TOOL_REGISTRY["test"][0]
        assert tool_name == ""

    def test_register_tool_special_characters_in_name(self) -> None:
        """Test registering with special characters in names."""

        @register_tool(domain="test-domain", tool_name="my_tool-v2.1")
        def tool() -> None:
            pass

        assert "test-domain" in TOOL_REGISTRY
        tool_name, _, _ = TOOL_REGISTRY["test-domain"][0]
        assert tool_name == "my_tool-v2.1"

    def test_register_tool_unicode_in_description(self) -> None:
        """Test registering with unicode characters in description."""

        @register_tool(
            domain="test",
            tool_name="tool",
            description="Tool with émojis 🚀 and ünïcödé",
        )
        def tool() -> None:
            pass

        _, _, description = TOOL_REGISTRY["test"][0]
        assert "🚀" in description
        assert "ünïcödé" in description

    def test_register_same_tool_name_different_domains(self) -> None:
        """Test registering same tool name in different domains."""

        @register_tool(domain="domain_a", tool_name="echo")
        def echo_a() -> str:
            return "a"

        @register_tool(domain="domain_b", tool_name="echo")
        def echo_b() -> str:
            return "b"

        assert len(TOOL_REGISTRY["domain_a"]) == 1
        assert len(TOOL_REGISTRY["domain_b"]) == 1

    def test_register_duplicate_tool_same_domain(self) -> None:
        """Test registering duplicate tool name in same domain adds both."""
        # Note: This might be considered a bug, but testing current behavior

        @register_tool(domain="test", tool_name="duplicate")
        def duplicate1() -> str:
            return "1"

        @register_tool(domain="test", tool_name="duplicate")
        def duplicate2() -> str:
            return "2"

        # Both are added (current behavior)
        assert len(TOOL_REGISTRY["test"]) == 2

    @pytest.mark.asyncio
    async def test_load_tools_with_path_object(self) -> None:
        """Test load_tools_from_registry accepts Path object."""
        config_data = {
            "version": "1.0",
            "domains": {
                "test": {
                    "tools": [
                        {
                            "name": "tool",
                            "description": "Test",
                            "handler_name": "h",
                            "category": "test",
                            "is_active": True,
                        }
                    ]
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)

        try:

            @register_tool(domain="test", tool_name="tool")
            async def tool() -> str:
                return "test"

            mock_mcp = MagicMock()
            mock_mcp.tool = MagicMock(return_value=lambda f: f)

            # Should work with Path object
            await load_tools_from_registry(mock_mcp, domain="test", config_path=temp_path)

            mock_mcp.tool.assert_called_once()
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_load_tools_transport_parameter_ignored(self) -> None:
        """Test that transport parameter is accepted but not used."""
        config_data = {
            "version": "1.0",
            "domains": {
                "test": {
                    "tools": [
                        {
                            "name": "tool",
                            "description": "Test",
                            "handler_name": "h",
                            "category": "test",
                            "is_active": True,
                        }
                    ]
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:

            @register_tool(domain="test", tool_name="tool")
            async def tool() -> str:
                return "test"

            mock_mcp = MagicMock()
            mock_mcp.tool = MagicMock(return_value=lambda f: f)

            # Should work with any transport value
            await load_tools_from_registry(
                mock_mcp, domain="test", transport="any_value", config_path=temp_path
            )

            mock_mcp.tool.assert_called_once()
        finally:
            Path(temp_path).unlink()


class TestIntegrationWithActualConfig:
    """Integration tests with actual config file."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        TOOL_REGISTRY.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        TOOL_REGISTRY.clear()

    @pytest.mark.asyncio
    async def test_load_from_actual_config_general_domain(self) -> None:
        """Test loading from actual config for general domain."""
        actual_config = Path(__file__).parent.parent.parent.parent / "config" / "tools.json"
        if not actual_config.exists():
            pytest.skip(f"Config file not found: {actual_config}")

        # Register a tool that should be in the actual config
        @register_tool(domain="general", tool_name="echo", description="Test echo")
        async def echo(text: str) -> dict[str, Any]:
            return {"text": text}

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        await load_tools_from_registry(mock_mcp, domain="general", config_path=actual_config)

        # Should have registered the echo tool
        mock_mcp.tool.assert_called()

    @pytest.mark.asyncio
    async def test_load_from_actual_config_cobol_domain(self) -> None:
        """Test loading from actual config for cobol_analysis domain."""
        actual_config = Path(__file__).parent.parent.parent.parent / "config" / "tools.json"
        if not actual_config.exists():
            pytest.skip(f"Config file not found: {actual_config}")

        # Register a tool that should be in the actual config
        @register_tool(domain="cobol_analysis", tool_name="build_ast")
        async def build_ast() -> dict[str, Any]:
            return {}

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        await load_tools_from_registry(mock_mcp, domain="cobol_analysis", config_path=actual_config)

        # Should have registered the build_ast tool
        mock_mcp.tool.assert_called()

"""Tests for decorator-based tool registry."""

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from src.mcp_servers.common.config_loader import ToolConfig
from src.mcp_servers.common.tool_registry import (
    TOOL_REGISTRY,
    load_tools_from_registry,
    register_tool,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the tool registry before each test."""
    TOOL_REGISTRY.clear()
    yield
    TOOL_REGISTRY.clear()


class TestToolRegistration:
    """Test tool registration via decorators."""

    def test_register_tool_basic(self):
        """Test basic tool registration."""

        @register_tool(domain="test", tool_name="test_tool", description="Test tool")
        async def test_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        # Verify tool is registered
        assert "test" in TOOL_REGISTRY
        assert len(TOOL_REGISTRY["test"]) == 1

        tool_name, tool_func, description = TOOL_REGISTRY["test"][0]
        assert tool_name == "test_tool"
        assert tool_func == test_tool
        assert description == "Test tool"

    def test_register_multiple_tools_same_domain(self):
        """Test registering multiple tools in the same domain."""

        @register_tool(domain="test", tool_name="tool1", description="Tool 1")
        async def tool1(param: str) -> dict[str, Any]:
            return {"result": param}

        @register_tool(domain="test", tool_name="tool2", description="Tool 2")
        async def tool2(param: int) -> dict[str, Any]:
            return {"result": param}

        # Verify both tools are registered
        assert "test" in TOOL_REGISTRY
        assert len(TOOL_REGISTRY["test"]) == 2

        tool_names = [name for name, _, _ in TOOL_REGISTRY["test"]]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    def test_register_tools_different_domains(self):
        """Test registering tools in different domains."""

        @register_tool(domain="domain1", tool_name="tool1", description="Tool 1")
        async def tool1(param: str) -> dict[str, Any]:
            return {"result": param}

        @register_tool(domain="domain2", tool_name="tool2", description="Tool 2")
        async def tool2(param: int) -> dict[str, Any]:
            return {"result": param}

        # Verify tools are in separate domains
        assert "domain1" in TOOL_REGISTRY
        assert "domain2" in TOOL_REGISTRY
        assert len(TOOL_REGISTRY["domain1"]) == 1
        assert len(TOOL_REGISTRY["domain2"]) == 1

    def test_register_tool_preserves_function(self):
        """Test that decorator preserves the original function."""

        async def original_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        decorated_tool = register_tool(domain="test", tool_name="test_tool", description="Test")(
            original_tool
        )

        # Verify function is preserved
        assert decorated_tool == original_tool
        assert decorated_tool.__name__ == original_tool.__name__


class TestLoadToolsFromRegistry:
    """Test loading tools from registry."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance."""
        mcp = MagicMock(spec=FastMCP)
        mcp._dynamic_tools = []

        def tool_factory(
            *, name: str, description: str = ""
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

        mcp.tool = MagicMock(side_effect=tool_factory)
        return mcp

    @pytest.mark.asyncio
    async def test_load_tools_from_registry_basic(self, mock_mcp):
        """Test basic tool loading from registry."""

        # Register a tool
        @register_tool(domain="test", tool_name="test_tool", description="Test tool")
        async def test_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        with patch(
            "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
            return_value=[
                ToolConfig(
                    name="test_tool",
                    description="Test tool from config",
                    handler_name="test_handler",
                    category="test",
                    is_active=True,
                )
            ],
        ):
            # Load tools from registry
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify tool was registered
        dynamic_tools = cast(list[Any], getattr(mock_mcp, "_dynamic_tools", []))
        assert len(dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_load_tools_filters_by_active_flag(self, mock_mcp):
        """Test that only active tools are loaded."""

        # Register two tools
        @register_tool(domain="test", tool_name="active_tool", description="Active")
        async def active_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        @register_tool(domain="test", tool_name="inactive_tool", description="Inactive")
        async def inactive_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        with patch(
            "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
            return_value=[
                ToolConfig(
                    name="active_tool",
                    description="Active tool",
                    handler_name="active_handler",
                    category="test",
                    is_active=True,
                )
            ],
        ):
            # Load tools from registry
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify only active tool was registered
        dynamic_tools = cast(list[Any], getattr(mock_mcp, "_dynamic_tools", []))
        assert len(dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_load_tools_empty_registry(self, mock_mcp):
        """Test loading from empty registry."""
        # Don't register any tools

        # Load tools from registry (should not raise)
        await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify no tools registered
        dynamic_tools = cast(list[Any], getattr(mock_mcp, "_dynamic_tools", []))
        assert len(dynamic_tools) == 0

    @pytest.mark.asyncio
    async def test_load_tools_no_active_in_config(self, mock_mcp):
        """Test when tools are registered but none are active in config."""

        # Register tools
        @register_tool(domain="test", tool_name="tool1", description="Tool 1")
        async def tool1(param: str) -> dict[str, Any]:
            return {"result": param}

        with patch(
            "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
            return_value=[],
        ):
            # Load tools from registry
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify no tools registered
        dynamic_tools = cast(list[Any], getattr(mock_mcp, "_dynamic_tools", []))
        assert len(dynamic_tools) == 0

    @pytest.mark.asyncio
    async def test_load_tools_uses_config_description(self, mock_mcp):
        """Test that config description is used over decorator description."""

        # Register a tool
        @register_tool(domain="test", tool_name="test_tool", description="Decorator desc")
        async def test_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        with patch(
            "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
            return_value=[
                ToolConfig(
                    name="test_tool",
                    description="Config description",
                    handler_name="test_handler",
                    category="test",
                    is_active=True,
                )
            ],
        ):
            # Load tools from registry
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify tool was registered (description is internal, can't verify externally)
        dynamic_tools = cast(list[Any], getattr(mock_mcp, "_dynamic_tools", []))
        assert len(dynamic_tools) == 1
        assert any(
            getattr(call, "kwargs", {}).get("description") == "Config description"
            for call in mock_mcp.tool.call_args_list
        )

    @pytest.mark.asyncio
    async def test_load_tools_warns_about_missing_in_code(self, mock_mcp, caplog):
        """Test warning when config has tools not in registry."""

        # Register one tool
        @register_tool(domain="test", tool_name="registered_tool", description="Registered")
        async def registered_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        with patch(
            "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
            return_value=[
                ToolConfig(
                    name="registered_tool",
                    description="Registered tool",
                    handler_name="handler1",
                    category="test",
                    is_active=True,
                ),
                ToolConfig(
                    name="missing_tool",
                    description="Missing tool",
                    handler_name="handler2",
                    category="test",
                    is_active=True,
                ),
            ],
        ):
            # Load tools from registry
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify only registered tool was loaded
        dynamic_tools = cast(list[Any], getattr(mock_mcp, "_dynamic_tools", []))
        assert len(dynamic_tools) == 1

        # Verify warning was logged
        assert "missing_tool" in caplog.text or "not registered in code" in caplog.text


class TestMultipleDomains:
    """Test tool registry with multiple domains."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance."""
        mcp = MagicMock(spec=FastMCP)
        mcp._dynamic_tools = []

        def tool_factory(
            *, name: str, description: str = ""
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

        mcp.tool = MagicMock(side_effect=tool_factory)
        return mcp

    @pytest.mark.asyncio
    async def test_load_tools_filters_by_domain(self, mock_mcp):
        """Test that loading tools filters by domain."""

        # Register tools in different domains
        @register_tool(domain="domain1", tool_name="tool1", description="Tool 1")
        async def tool1(param: str) -> dict[str, Any]:
            return {"result": param}

        @register_tool(domain="domain2", tool_name="tool2", description="Tool 2")
        async def tool2(param: str) -> dict[str, Any]:
            return {"result": param}

        def active_tools(domain: str, _config_path: Any = "config/tools.json") -> list[ToolConfig]:
            if domain == "domain1":
                return [
                    ToolConfig(
                        name="tool1",
                        description="Tool 1",
                        handler_name="handler1",
                        category="test",
                        is_active=True,
                    )
                ]
            return []

        with patch(
            "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
            side_effect=active_tools,
        ):
            # Load tools for domain1
            await load_tools_from_registry(mock_mcp, domain="domain1", transport="stdio")

        # Verify only domain1 tool was registered
        dynamic_tools = cast(list[Any], getattr(mock_mcp, "_dynamic_tools", []))
        assert len(dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_load_tools_multiple_domains_sequential(self):
        """Test loading tools from multiple domains sequentially."""

        # Register tools in different domains
        @register_tool(domain="domain1", tool_name="tool1", description="Tool 1")
        async def tool1(param: str) -> dict[str, Any]:
            return {"result": param}

        @register_tool(domain="domain2", tool_name="tool2", description="Tool 2")
        async def tool2(param: str) -> dict[str, Any]:
            return {"result": param}

        # Create separate MCP instances
        mcp1 = MagicMock(spec=FastMCP)
        mcp1._dynamic_tools = []
        mcp2 = MagicMock(spec=FastMCP)
        mcp2._dynamic_tools = []

        def tool_factory(
            *, name: str, description: str = ""
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

        mcp1.tool = MagicMock(side_effect=tool_factory)
        mcp2.tool = MagicMock(side_effect=tool_factory)

        def active_tools(domain: str, _config_path: Any = "config/tools.json") -> list[ToolConfig]:
            if domain == "domain1":
                return [
                    ToolConfig(
                        name="tool1",
                        description="Tool 1",
                        handler_name="handler1",
                        category="test",
                        is_active=True,
                    )
                ]
            if domain == "domain2":
                return [
                    ToolConfig(
                        name="tool2",
                        description="Tool 2",
                        handler_name="handler2",
                        category="test",
                        is_active=True,
                    )
                ]
            return []

        with patch(
            "src.mcp_servers.common.tool_registry.get_active_tools_for_domain",
            side_effect=active_tools,
        ):
            await load_tools_from_registry(mcp1, domain="domain1", transport="stdio")
            await load_tools_from_registry(mcp2, domain="domain2", transport="stdio")

        assert len(cast(list[Any], getattr(mcp1, "_dynamic_tools", []))) == 1
        assert len(cast(list[Any], getattr(mcp2, "_dynamic_tools", []))) == 1

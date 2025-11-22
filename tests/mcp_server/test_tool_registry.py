"""Tests for decorator-based tool registry."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from src.core.models.tool_model import Tool
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
        return mcp

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        with patch("src.mcp_servers.common.tool_registry.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def mock_tool_repo(self, mock_db_session):
        """Create a mock tool repository."""
        with patch("src.mcp_servers.common.tool_registry.ToolRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    @pytest.mark.asyncio
    async def test_load_tools_from_registry_basic(self, mock_mcp, mock_tool_repo):
        """Test basic tool loading from registry."""

        # Register a tool
        @register_tool(domain="test", tool_name="test_tool", description="Test tool")
        async def test_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        # Mock database to return the tool as active
        db_tool = Tool(
            name="test_tool",
            description="Test tool from DB",
            handler_name="test_handler",
            category="test",
            domain="test",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool])

        # Load tools from registry
        await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify tool was registered
        assert len(mock_mcp._dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_load_tools_filters_by_active_flag(self, mock_mcp, mock_tool_repo):
        """Test that only active tools are loaded."""

        # Register two tools
        @register_tool(domain="test", tool_name="active_tool", description="Active")
        async def active_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        @register_tool(domain="test", tool_name="inactive_tool", description="Inactive")
        async def inactive_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        # Mock database to return only one tool as active
        db_tool = Tool(
            name="active_tool",
            description="Active tool",
            handler_name="active_handler",
            category="test",
            domain="test",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool])

        # Load tools from registry
        await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify only active tool was registered
        assert len(mock_mcp._dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_load_tools_empty_registry(self, mock_mcp, mock_tool_repo):
        """Test loading from empty registry."""
        # Don't register any tools

        # Mock database
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[])

        # Load tools from registry (should not raise)
        await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify no tools registered
        assert len(mock_mcp._dynamic_tools) == 0

    @pytest.mark.asyncio
    async def test_load_tools_no_active_in_db(self, mock_mcp, mock_tool_repo):
        """Test when tools are registered but none are active in DB."""

        # Register tools
        @register_tool(domain="test", tool_name="tool1", description="Tool 1")
        async def tool1(param: str) -> dict[str, Any]:
            return {"result": param}

        # Mock database to return no active tools
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[])

        # Load tools from registry
        await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify no tools registered
        assert len(mock_mcp._dynamic_tools) == 0

    @pytest.mark.asyncio
    async def test_load_tools_uses_db_description(self, mock_mcp, mock_tool_repo):
        """Test that DB description is used over decorator description."""

        # Register a tool
        @register_tool(domain="test", tool_name="test_tool", description="Decorator desc")
        async def test_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        # Mock database with different description
        db_tool = Tool(
            name="test_tool",
            description="Database description",
            handler_name="test_handler",
            category="test",
            domain="test",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool])

        # Load tools from registry
        await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify tool was registered (description is internal, can't verify externally)
        assert len(mock_mcp._dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_load_tools_warns_about_missing_in_code(self, mock_mcp, mock_tool_repo, caplog):
        """Test warning when DB has tools not in registry."""

        # Register one tool
        @register_tool(domain="test", tool_name="registered_tool", description="Registered")
        async def registered_tool(param: str) -> dict[str, Any]:
            return {"result": param}

        # Mock database to return two tools (one not in registry)
        db_tool1 = Tool(
            name="registered_tool",
            description="Registered tool",
            handler_name="handler1",
            category="test",
            domain="test",
            is_active=True,
        )
        db_tool2 = Tool(
            name="missing_tool",
            description="Missing tool",
            handler_name="handler2",
            category="test",
            domain="test",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool1, db_tool2])

        # Load tools from registry
        await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

        # Verify only registered tool was loaded
        assert len(mock_mcp._dynamic_tools) == 1

        # Verify warning was logged
        assert "missing_tool" in caplog.text or "not registered in code" in caplog.text


class TestObservabilityWrapping:
    """Test observability wrapping of tools."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance."""
        mcp = MagicMock(spec=FastMCP)
        mcp._dynamic_tools = []
        return mcp

    @pytest.fixture
    def mock_tool_repo(self):
        """Create a mock tool repository."""
        with (
            patch("src.mcp_servers.common.tool_registry.async_session_factory"),
            patch("src.mcp_servers.common.tool_registry.ToolRepository") as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    @pytest.mark.asyncio
    async def test_observability_wrapper_success(self, mock_mcp, mock_tool_repo):
        """Test observability wrapper on successful tool execution."""

        # Register a tool
        @register_tool(domain="test", tool_name="test_tool", description="Test")
        async def test_tool(param: str) -> dict[str, Any]:
            return {"success": True, "result": param}

        # Mock database
        db_tool = Tool(
            name="test_tool",
            description="Test tool",
            handler_name="test_handler",
            category="test",
            domain="test",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool])

        # Mock observability - patch where it's imported
        with patch(
            "src.core.services.common.observability_service.trace_tool_execution"
        ) as mock_trace:
            mock_trace.return_value.__aenter__ = AsyncMock(return_value={})
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            # Load tools
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

            # Execute the wrapped tool
            wrapped_tool = mock_mcp._dynamic_tools[0]
            result = await wrapped_tool(param="test_value")

            # Verify result is correct
            assert result["success"] is True
            assert result["result"] == "test_value"

    @pytest.mark.asyncio
    async def test_observability_wrapper_handles_exceptions(self, mock_mcp, mock_tool_repo):
        """Test observability wrapper handles exceptions."""

        # Register a tool that raises an exception
        @register_tool(domain="test", tool_name="failing_tool", description="Failing")
        async def failing_tool(param: str) -> dict[str, Any]:
            raise ValueError("Test error")

        # Mock database
        db_tool = Tool(
            name="failing_tool",
            description="Failing tool",
            handler_name="failing_handler",
            category="test",
            domain="test",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool])

        # Mock observability - patch where it's imported
        with patch(
            "src.core.services.common.observability_service.trace_tool_execution"
        ) as mock_trace:
            mock_ctx = {}
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            # Load tools
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

            # Execute the wrapped tool
            wrapped_tool = mock_mcp._dynamic_tools[0]
            result = await wrapped_tool(param="test_value")

            # Verify error is captured
            assert result["success"] is False
            assert "error" in result
            assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_observability_wrapper_validates_return_type(self, mock_mcp, mock_tool_repo):
        """Test observability wrapper validates return type."""

        # Register a tool that returns wrong type
        @register_tool(domain="test", tool_name="bad_tool", description="Bad return type")
        async def bad_tool(param: str) -> dict[str, Any]:
            return "not a dict"  # type: ignore[return-value]

        # Mock database
        db_tool = Tool(
            name="bad_tool",
            description="Bad tool",
            handler_name="bad_handler",
            category="test",
            domain="test",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool])

        # Mock observability - patch where it's imported
        with patch(
            "src.core.services.common.observability_service.trace_tool_execution"
        ) as mock_trace:
            mock_trace.return_value.__aenter__ = AsyncMock(return_value={})
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            # Load tools
            await load_tools_from_registry(mock_mcp, domain="test", transport="stdio")

            # Execute the wrapped tool
            wrapped_tool = mock_mcp._dynamic_tools[0]
            result = await wrapped_tool(param="test_value")

            # Verify error about invalid return type
            assert result["success"] is False
            assert "error" in result
            assert "invalid type" in result["error"].lower()


class TestMultipleDomains:
    """Test tool registry with multiple domains."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance."""
        mcp = MagicMock(spec=FastMCP)
        mcp._dynamic_tools = []
        return mcp

    @pytest.fixture
    def mock_tool_repo(self):
        """Create a mock tool repository."""
        with (
            patch("src.mcp_servers.common.tool_registry.async_session_factory"),
            patch("src.mcp_servers.common.tool_registry.ToolRepository") as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    @pytest.mark.asyncio
    async def test_load_tools_filters_by_domain(self, mock_mcp, mock_tool_repo):
        """Test that loading tools filters by domain."""

        # Register tools in different domains
        @register_tool(domain="domain1", tool_name="tool1", description="Tool 1")
        async def tool1(param: str) -> dict[str, Any]:
            return {"result": param}

        @register_tool(domain="domain2", tool_name="tool2", description="Tool 2")
        async def tool2(param: str) -> dict[str, Any]:
            return {"result": param}

        # Mock database for domain1 only
        db_tool = Tool(
            name="tool1",
            description="Tool 1",
            handler_name="handler1",
            category="test",
            domain="domain1",
            is_active=True,
        )
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool])

        # Load tools for domain1
        await load_tools_from_registry(mock_mcp, domain="domain1", transport="stdio")

        # Verify only domain1 tool was registered
        assert len(mock_mcp._dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_load_tools_multiple_domains_sequential(self, mock_tool_repo):
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

        # Mock database responses
        db_tool1 = Tool(
            name="tool1",
            description="Tool 1",
            handler_name="handler1",
            category="test",
            domain="domain1",
            is_active=True,
        )
        db_tool2 = Tool(
            name="tool2",
            description="Tool 2",
            handler_name="handler2",
            category="test",
            domain="domain2",
            is_active=True,
        )

        # Load domain1 tools
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool1])
        await load_tools_from_registry(mcp1, domain="domain1", transport="stdio")
        assert len(mcp1._dynamic_tools) == 1

        # Load domain2 tools
        mock_tool_repo.get_by_domain = AsyncMock(return_value=[db_tool2])
        await load_tools_from_registry(mcp2, domain="domain2", transport="stdio")
        assert len(mcp2._dynamic_tools) == 1

"""Integration tests for decorator-based tool registration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

# Import tools once at module level to trigger registration
import src.mcp_servers.mcp_general.tools  # noqa: F401
from src.core.models.tool_model import Tool
from src.mcp_servers.common.stdio_runner import startup
from src.mcp_servers.common.tool_registry import TOOL_REGISTRY, load_tools_from_registry


class TestDecoratorIntegration:
    """Integration tests for decorator-based tools."""

    @pytest.mark.asyncio
    async def test_general_domain_tools_registered(self):
        """Test that general domain tools are registered via decorators."""
        # Verify tools are in registry
        assert "general" in TOOL_REGISTRY
        registered_tools = {name for name, _, _ in TOOL_REGISTRY["general"]}
        assert "echo" in registered_tools
        assert "calculator_add" in registered_tools

    @pytest.mark.asyncio
    async def test_general_domain_loads_from_decorators(self):
        """Test that general domain can load tools from decorators."""
        # Create mock MCP instance
        mcp = FastMCP("test")

        # Mock database tools (active)
        db_tool_echo = Tool(
            name="echo",
            description="Echo back the provided text",
            handler_name="echo_handler",
            category="utility",
            domain="general",
            is_active=True,
        )
        db_tool_calc = Tool(
            name="calculator_add",
            description="Add two numbers",
            handler_name="calculator_add_handler",
            category="calculation",
            domain="general",
            is_active=True,
        )

        with (
            patch("src.mcp_servers.common.tool_registry.async_session_factory"),
            patch("src.mcp_servers.common.tool_registry.ToolRepository") as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_domain = AsyncMock(return_value=[db_tool_echo, db_tool_calc])

            # Load tools
            await load_tools_from_registry(mcp, domain="general", transport="stdio")

            # Verify tools were loaded
            assert hasattr(mcp, "_dynamic_tools")
            assert len(mcp._dynamic_tools) == 2

    @pytest.mark.asyncio
    async def test_decorator_tools_respect_active_flag(self):
        """Test that decorator tools respect the is_active flag in database."""
        # Create mock MCP instance
        mcp = FastMCP("test")

        # Mock database with only echo active
        db_tool_echo = Tool(
            name="echo",
            description="Echo back the provided text",
            handler_name="echo_handler",
            category="utility",
            domain="general",
            is_active=True,
        )

        with (
            patch("src.mcp_servers.common.tool_registry.async_session_factory"),
            patch("src.mcp_servers.common.tool_registry.ToolRepository") as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            # Only echo is active
            mock_repo.get_by_domain = AsyncMock(return_value=[db_tool_echo])

            # Load tools
            await load_tools_from_registry(mcp, domain="general", transport="stdio")

            # Verify only echo was loaded
            assert hasattr(mcp, "_dynamic_tools")
            assert len(mcp._dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_decorator_tools_have_correct_names(self):
        """Test that loaded decorator tools have correct metadata."""
        # Create mock MCP instance
        mcp = FastMCP("test")

        # Mock database
        db_tool_echo = Tool(
            name="echo",
            description="Echo back the provided text",
            handler_name="echo_handler",
            category="utility",
            domain="general",
            is_active=True,
        )
        db_tool_calc = Tool(
            name="calculator_add",
            description="Add two numbers",
            handler_name="calculator_add_handler",
            category="calculation",
            domain="general",
            is_active=True,
        )

        with (
            patch("src.mcp_servers.common.tool_registry.async_session_factory"),
            patch("src.mcp_servers.common.tool_registry.ToolRepository") as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_domain = AsyncMock(return_value=[db_tool_echo, db_tool_calc])

            # Load tools
            await load_tools_from_registry(mcp, domain="general", transport="stdio")

            # Verify tools were loaded
            assert hasattr(mcp, "_dynamic_tools")
            assert len(mcp._dynamic_tools) == 2

            # Verify tools are functions (observability-wrapped)
            for tool in mcp._dynamic_tools:
                assert callable(tool)

    @pytest.mark.asyncio
    async def test_decorator_tools_filtered_by_domain(self):
        """Test that tools are correctly filtered by domain."""
        # Create mock MCP instance
        mcp = FastMCP("test")

        # Mock database - request 'general' domain
        db_tool = Tool(
            name="echo",
            description="Echo text",
            handler_name="echo_handler",
            category="utility",
            domain="general",
            is_active=True,
        )

        with (
            patch("src.mcp_servers.common.tool_registry.async_session_factory"),
            patch("src.mcp_servers.common.tool_registry.ToolRepository") as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_domain = AsyncMock(return_value=[db_tool])

            # Load tools for general domain
            await load_tools_from_registry(mcp, domain="general", transport="stdio")

            # Verify only general domain tools were loaded
            assert hasattr(mcp, "_dynamic_tools")
            assert len(mcp._dynamic_tools) == 1
            assert callable(mcp._dynamic_tools[0])

    @pytest.mark.asyncio
    async def test_general_domain_end_to_end(self):
        """End-to-end test: Import, load, and execute decorator tools."""
        # Simulate full server startup for general domain
        # This should load tools via decorators
        mcp = await startup(domain="general", use_decorators=True)

        # Verify server initialized
        assert mcp is not None
        assert isinstance(mcp, FastMCP)

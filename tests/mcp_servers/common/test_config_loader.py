"""Tests for JSON configuration loader.

This module tests the config_loader functionality which is responsible for:
- Loading tools.json configuration file
- Parsing domain and tool configurations
- Filtering active tools for each domain
- Validating configuration structure
"""

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.mcp_servers.common.config_loader import (
    DomainConfig,
    ToolConfig,
    ToolsConfig,
    get_active_tools_for_domain,
    list_all_domains,
    load_tools_config,
)


# Path to actual config file
ACTUAL_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "tools.json"


class TestToolConfigModel:
    """Tests for ToolConfig Pydantic model."""

    def test_tool_config_required_fields(self) -> None:
        """Test ToolConfig with all required fields."""
        tool = ToolConfig(
            name="test_tool",
            description="A test tool",
            handler_name="test_handler",
            category="testing",
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.handler_name == "test_handler"
        assert tool.category == "testing"
        assert tool.is_active is True  # Default
        assert tool.parameters_schema == {}  # Default

    def test_tool_config_with_optional_fields(self) -> None:
        """Test ToolConfig with optional fields specified."""
        tool = ToolConfig(
            name="test_tool",
            description="A test tool",
            handler_name="test_handler",
            category="testing",
            is_active=False,
            parameters_schema={"type": "object", "properties": {}},
        )

        assert tool.is_active is False
        assert tool.parameters_schema == {"type": "object", "properties": {}}

    def test_tool_config_missing_required_field(self) -> None:
        """Test ToolConfig raises error when required field is missing."""
        with pytest.raises(ValidationError):
            ToolConfig(  # type: ignore[call-arg]
                name="test_tool",
                # Missing description, handler_name, category
            )


class TestDomainConfigModel:
    """Tests for DomainConfig Pydantic model."""

    def test_domain_config_empty_tools(self) -> None:
        """Test DomainConfig with no tools."""
        domain = DomainConfig()
        assert domain.tools == []

    def test_domain_config_with_tools(self) -> None:
        """Test DomainConfig with tools list."""
        domain = DomainConfig(
            tools=[
                ToolConfig(
                    name="tool1",
                    description="Tool 1",
                    handler_name="handler1",
                    category="cat1",
                ),
                ToolConfig(
                    name="tool2",
                    description="Tool 2",
                    handler_name="handler2",
                    category="cat2",
                ),
            ]
        )
        assert len(domain.tools) == 2
        assert domain.tools[0].name == "tool1"
        assert domain.tools[1].name == "tool2"


class TestToolsConfigModel:
    """Tests for ToolsConfig root model."""

    def test_tools_config_defaults(self) -> None:
        """Test ToolsConfig with default values."""
        config = ToolsConfig()
        assert config.version == "1.0"
        assert config.description == ""
        assert config.domains == {}

    def test_tools_config_with_domains(self) -> None:
        """Test ToolsConfig with domains."""
        config = ToolsConfig(
            version="2.0",
            description="Test config",
            domains={
                "general": DomainConfig(
                    tools=[
                        ToolConfig(
                            name="echo",
                            description="Echo tool",
                            handler_name="echo_handler",
                            category="utility",
                        )
                    ]
                )
            },
        )
        assert config.version == "2.0"
        assert config.description == "Test config"
        assert "general" in config.domains
        assert len(config.domains["general"].tools) == 1


class TestLoadToolsConfig:
    """Tests for load_tools_config function."""

    def test_load_actual_config_file(self) -> None:
        """Test loading the actual config/tools.json file."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        config = load_tools_config(ACTUAL_CONFIG_PATH)

        assert config.version is not None
        assert "general" in config.domains or "cobol_analysis" in config.domains

    def test_load_config_file_not_found(self) -> None:
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_tools_config("/nonexistent/path/tools.json")

        assert "not found" in str(exc_info.value).lower()

    def test_load_config_valid_json(self) -> None:
        """Test loading a valid JSON config file."""
        config_data = {
            "version": "1.0",
            "description": "Test configuration",
            "domains": {
                "test_domain": {
                    "tools": [
                        {
                            "name": "test_tool",
                            "description": "A test tool",
                            "handler_name": "test_handler",
                            "category": "testing",
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
            config = load_tools_config(temp_path)

            assert config.version == "1.0"
            assert config.description == "Test configuration"
            assert "test_domain" in config.domains
            assert len(config.domains["test_domain"].tools) == 1
            assert config.domains["test_domain"].tools[0].name == "test_tool"
        finally:
            Path(temp_path).unlink()

    def test_load_config_invalid_json(self) -> None:
        """Test error when JSON is invalid."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                load_tools_config(temp_path)

            assert "invalid json" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_load_config_empty_domains(self) -> None:
        """Test loading config with empty domains."""
        config_data = {
            "version": "1.0",
            "description": "Empty config",
            "domains": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_tools_config(temp_path)
            assert config.domains == {}
        finally:
            Path(temp_path).unlink()

    def test_load_config_multiple_domains(self) -> None:
        """Test loading config with multiple domains."""
        config_data = {
            "version": "1.0",
            "description": "Multi-domain config",
            "domains": {
                "general": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "Echo",
                            "handler_name": "echo_handler",
                            "category": "utility",
                        }
                    ]
                },
                "cobol_analysis": {
                    "tools": [
                        {
                            "name": "parse_cobol",
                            "description": "Parse COBOL",
                            "handler_name": "parse_cobol_handler",
                            "category": "parsing",
                        }
                    ]
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_tools_config(temp_path)
            assert len(config.domains) == 2
            assert "general" in config.domains
            assert "cobol_analysis" in config.domains
        finally:
            Path(temp_path).unlink()


class TestGetActiveToolsForDomain:
    """Tests for get_active_tools_for_domain function."""

    @pytest.fixture
    def temp_config_file(self) -> Iterator[str]:
        """Create a temporary config file for testing."""
        config_data = {
            "version": "1.0",
            "description": "Test config",
            "domains": {
                "general": {
                    "tools": [
                        {
                            "name": "active_tool",
                            "description": "Active tool",
                            "handler_name": "active_handler",
                            "category": "utility",
                            "is_active": True,
                        },
                        {
                            "name": "inactive_tool",
                            "description": "Inactive tool",
                            "handler_name": "inactive_handler",
                            "category": "utility",
                            "is_active": False,
                        },
                        {
                            "name": "another_active",
                            "description": "Another active tool",
                            "handler_name": "another_handler",
                            "category": "utility",
                            "is_active": True,
                        },
                    ]
                },
                "empty_domain": {"tools": []},
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        yield temp_path
        Path(temp_path).unlink()

    def test_get_active_tools_filters_inactive(self, temp_config_file: str) -> None:
        """Test that inactive tools are filtered out."""
        active_tools = get_active_tools_for_domain("general", temp_config_file)

        # Should only have 2 active tools, not 3
        assert len(active_tools) == 2
        tool_names = [t.name for t in active_tools]
        assert "active_tool" in tool_names
        assert "another_active" in tool_names
        assert "inactive_tool" not in tool_names

    def test_get_active_tools_nonexistent_domain(self, temp_config_file: str) -> None:
        """Test getting tools for a domain that doesn't exist."""
        active_tools = get_active_tools_for_domain("nonexistent", temp_config_file)
        assert active_tools == []

    def test_get_active_tools_empty_domain(self, temp_config_file: str) -> None:
        """Test getting tools for a domain with no tools."""
        active_tools = get_active_tools_for_domain("empty_domain", temp_config_file)
        assert active_tools == []

    def test_get_active_tools_returns_tool_config(self, temp_config_file: str) -> None:
        """Test that returned items are ToolConfig instances."""
        active_tools = get_active_tools_for_domain("general", temp_config_file)

        assert len(active_tools) > 0
        for tool in active_tools:
            assert isinstance(tool, ToolConfig)
            assert tool.name is not None
            assert tool.handler_name is not None

    def test_get_active_tools_from_actual_config(self) -> None:
        """Test getting active tools from actual config file."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        # Test general domain
        general_tools = get_active_tools_for_domain("general", ACTUAL_CONFIG_PATH)
        assert len(general_tools) >= 1  # At least echo and calculator_add

        # Test cobol_analysis domain
        cobol_tools = get_active_tools_for_domain("cobol_analysis", ACTUAL_CONFIG_PATH)
        assert len(cobol_tools) >= 1  # At least build_ast

        # Verify tool structure
        for tool in general_tools:
            assert tool.is_active is True
            assert tool.handler_name is not None


class TestListAllDomains:
    """Tests for list_all_domains function."""

    def test_list_domains_from_actual_config(self) -> None:
        """Test listing domains from actual config file."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        domains = list_all_domains(ACTUAL_CONFIG_PATH)

        assert isinstance(domains, list)
        assert "general" in domains or "cobol_analysis" in domains

    def test_list_domains_empty_config(self) -> None:
        """Test listing domains from config with no domains."""
        config_data = {
            "version": "1.0",
            "description": "Empty config",
            "domains": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            domains = list_all_domains(temp_path)
            assert domains == []
        finally:
            Path(temp_path).unlink()

    def test_list_domains_multiple(self) -> None:
        """Test listing multiple domains."""
        config_data = {
            "version": "1.0",
            "domains": {
                "domain_a": {"tools": []},
                "domain_b": {"tools": []},
                "domain_c": {"tools": []},
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            domains = list_all_domains(temp_path)
            assert len(domains) == 3
            assert "domain_a" in domains
            assert "domain_b" in domains
            assert "domain_c" in domains
        finally:
            Path(temp_path).unlink()


class TestActualConfigIntegrity:
    """Tests to verify the actual config/tools.json is valid and complete."""

    def test_actual_config_loads_successfully(self) -> None:
        """Test that actual config file loads without errors."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        config = load_tools_config(ACTUAL_CONFIG_PATH)
        assert config is not None
        assert config.version is not None

    def test_actual_config_has_required_domains(self) -> None:
        """Test that actual config has expected domains."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        config = load_tools_config(ACTUAL_CONFIG_PATH)

        # These domains should exist
        expected_domains = ["general", "cobol_analysis"]
        for domain in expected_domains:
            assert domain in config.domains, f"Missing domain: {domain}"

    def test_actual_config_general_domain_tools(self) -> None:
        """Test that general domain has expected tools."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        active_tools = get_active_tools_for_domain("general", ACTUAL_CONFIG_PATH)
        tool_names = [t.name for t in active_tools]

        # Echo and calculator_add should be present and active
        assert "echo" in tool_names, "Missing tool: echo"
        assert "calculator_add" in tool_names, "Missing tool: calculator_add"

    def test_actual_config_cobol_domain_tools(self) -> None:
        """Test that cobol_analysis domain has expected tools."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        active_tools = get_active_tools_for_domain("cobol_analysis", ACTUAL_CONFIG_PATH)
        tool_names = [t.name for t in active_tools]

        # Key COBOL tools should be present and active
        expected_tools = ["build_ast", "build_asg", "parse_cobol", "analyze_complexity"]
        for tool in expected_tools:
            assert tool in tool_names, f"Missing tool: {tool}"

    def test_actual_config_all_tools_have_handlers(self) -> None:
        """Test that all tools in actual config have handler names."""
        if not ACTUAL_CONFIG_PATH.exists():
            pytest.skip(f"Config file not found: {ACTUAL_CONFIG_PATH}")

        config = load_tools_config(ACTUAL_CONFIG_PATH)

        for domain_name, domain_config in config.domains.items():
            for tool in domain_config.tools:
                assert (
                    tool.handler_name
                ), f"Tool '{tool.name}' in domain '{domain_name}' has no handler_name"
                assert tool.handler_name.endswith(
                    "_handler"
                ), f"Handler '{tool.handler_name}' should end with '_handler'"

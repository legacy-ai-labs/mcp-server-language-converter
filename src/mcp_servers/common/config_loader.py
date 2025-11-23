"""JSON configuration loader for tool definitions.

This module provides functionality to load tool configurations from a JSON file,
replacing the database-driven approach with a simpler, version-controllable solution.
"""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ToolConfig(BaseModel):
    """Configuration for a single tool."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    handler_name: str = Field(..., description="Handler function name")
    category: str = Field(..., description="Tool category")
    is_active: bool = Field(default=True, description="Whether tool is active")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict, description="Optional JSON schema for parameters"
    )


class DomainConfig(BaseModel):
    """Configuration for a domain."""

    tools: list[ToolConfig] = Field(
        default_factory=list, description="List of tools in this domain"
    )


class ToolsConfig(BaseModel):
    """Root configuration structure."""

    version: str = Field(default="1.0", description="Configuration version")
    description: str = Field(default="", description="Configuration description")
    domains: dict[str, DomainConfig] = Field(
        default_factory=dict, description="Domain configurations"
    )


def load_tools_config(config_path: str | Path = "config/tools.json") -> ToolsConfig:
    """Load tools configuration from JSON file.

    Args:
        config_path: Path to the JSON configuration file

    Returns:
        ToolsConfig instance with loaded configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If JSON is invalid or doesn't match schema
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Tools configuration file not found: {config_path}")

    logger.info(f"Loading tools configuration from {config_path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        config = ToolsConfig.model_validate(data)
        logger.info(
            f"Loaded configuration version {config.version} with {len(config.domains)} domains"
        )
        return config

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}") from e


def get_active_tools_for_domain(
    domain: str, config_path: str | Path = "config/tools.json"
) -> list[ToolConfig]:
    """Get active tools for a specific domain from configuration.

    Args:
        domain: Domain name to filter by
        config_path: Path to the JSON configuration file

    Returns:
        List of active ToolConfig instances for the domain
    """
    config = load_tools_config(config_path)

    if domain not in config.domains:
        logger.warning(f"Domain '{domain}' not found in configuration")
        return []

    domain_config = config.domains[domain]
    active_tools = [tool for tool in domain_config.tools if tool.is_active]

    logger.debug(f"Found {len(active_tools)} active tools for domain '{domain}'")
    return active_tools


def list_all_domains(config_path: str | Path = "config/tools.json") -> list[str]:
    """List all domains defined in the configuration.

    Args:
        config_path: Path to the JSON configuration file

    Returns:
        List of domain names
    """
    config = load_tools_config(config_path)
    return list(config.domains.keys())

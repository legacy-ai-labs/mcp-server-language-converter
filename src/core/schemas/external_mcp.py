"""Pydantic schemas for external MCP validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExternalMCPServerBase(BaseModel):
    """Base schema for external MCP server."""

    name: str = Field(..., min_length=1, max_length=100, description="Server name")
    display_name: str = Field(..., min_length=1, max_length=200, description="Display name")
    command: str = Field(..., description="Command to start the server (JSON string)")
    working_directory: str = Field(..., description="Working directory for the server")
    is_active: bool = Field(default=True, description="Whether the server is active")
    connection_timeout: int = Field(
        default=30, ge=1, le=300, description="Connection timeout in seconds"
    )
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")


class ExternalMCPServerCreate(ExternalMCPServerBase):
    """Schema for creating a new external MCP server."""

    pass


class ExternalMCPServerUpdate(BaseModel):
    """Schema for updating an external MCP server."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Server name")
    display_name: str | None = Field(None, min_length=1, max_length=200, description="Display name")
    command: str | None = Field(None, description="Command to start the server (JSON string)")
    working_directory: str | None = Field(None, description="Working directory for the server")
    is_active: bool | None = Field(None, description="Whether the server is active")
    connection_timeout: int | None = Field(
        None, ge=1, le=300, description="Connection timeout in seconds"
    )
    retry_attempts: int | None = Field(None, ge=0, le=10, description="Number of retry attempts")


class ExternalMCPServerResponse(ExternalMCPServerBase):
    """Schema for external MCP server response."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExternalMCPToolBase(BaseModel):
    """Base schema for external MCP tool."""

    server_id: int = Field(..., description="Server ID")
    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    full_name: str = Field(
        ..., min_length=1, max_length=200, description="Full tool name with namespace"
    )
    description: str = Field(..., min_length=1, description="Tool description")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema for parameters"
    )
    is_active: bool = Field(default=True, description="Whether the tool is active")


class ExternalMCPToolCreate(ExternalMCPToolBase):
    """Schema for creating a new external MCP tool."""

    pass


class ExternalMCPToolUpdate(BaseModel):
    """Schema for updating an external MCP tool."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Tool name")
    full_name: str | None = Field(
        None, min_length=1, max_length=200, description="Full tool name with namespace"
    )
    description: str | None = Field(None, min_length=1, description="Tool description")
    parameters_schema: dict[str, Any] | None = Field(None, description="JSON schema for parameters")
    is_active: bool | None = Field(None, description="Whether the tool is active")


class ExternalMCPToolResponse(ExternalMCPToolBase):
    """Schema for external MCP tool response."""

    id: int
    last_discovered: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExternalMCPStatusBase(BaseModel):
    """Base schema for external MCP status."""

    server_id: int = Field(..., description="Server ID")
    status: str = Field(
        ..., min_length=1, max_length=20, description="Status (connected, disconnected, error)"
    )
    error_message: str | None = Field(None, description="Error message if status is error")
    response_time_ms: int | None = Field(None, ge=0, description="Response time in milliseconds")


class ExternalMCPStatusCreate(ExternalMCPStatusBase):
    """Schema for creating a new external MCP status."""

    pass


class ExternalMCPStatusResponse(ExternalMCPStatusBase):
    """Schema for external MCP status response."""

    id: int
    last_check: datetime

    model_config = ConfigDict(from_attributes=True)

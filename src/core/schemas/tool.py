"""Pydantic schemas for Tool validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolBase(BaseModel):
    """Base schema for Tool."""

    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    description: str = Field(..., min_length=1, description="Tool description")
    handler_name: str = Field(
        ..., min_length=1, max_length=100, description="Handler function name"
    )
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema for tool parameters"
    )
    category: str = Field(..., min_length=1, max_length=50, description="Tool category")
    domain: str = Field(..., min_length=1, max_length=50, description="Tool domain")
    is_active: bool = Field(default=True, description="Whether the tool is active")


class ToolCreate(ToolBase):
    """Schema for creating a new tool."""

    pass


class ToolUpdate(BaseModel):
    """Schema for updating a tool."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Tool name")
    description: str | None = Field(None, min_length=1, description="Tool description")
    handler_name: str | None = Field(
        None, min_length=1, max_length=100, description="Handler function name"
    )
    parameters_schema: dict[str, Any] | None = Field(
        None, description="JSON schema for tool parameters"
    )
    category: str | None = Field(None, min_length=1, max_length=50, description="Tool category")
    domain: str | None = Field(None, min_length=1, max_length=50, description="Tool domain")
    is_active: bool | None = Field(None, description="Whether the tool is active")


class ToolResponse(ToolBase):
    """Schema for tool response."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

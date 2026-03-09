"""Pydantic request/response models for the ProLeap Java service."""

from typing import Any

from pydantic import BaseModel, Field


class ProLeapRequest(BaseModel):
    """Request payload sent to the ProLeap service."""

    code: str = Field(..., description="COBOL source code")
    format: str = Field(default="FIXED", description="COBOL format: FIXED or FREE")


class ProLeapResponse(BaseModel):
    """Generic response from the ProLeap service."""

    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None


class ProLeapHealthStatus(BaseModel):
    """Health check response from the ProLeap service."""

    status: str
    version: str
    capabilities: list[str]

"""Core business logic module.

This module contains transport-agnostic business logic that can be reused
across both MCP and REST API interfaces.

All business logic should be implemented here to maintain a single source of truth.
"""

from src.core.config import Settings, get_settings
from src.core.database import Base, get_session, init_db
from src.core.exceptions import (
    ApplicationError,
    DatabaseError,
    NotFoundError,
    ToolHandlerError,
    ToolHandlerNotFoundError,
    ToolNotFoundError,
    ValidationError,
)


__all__: list[str] = [
    "ApplicationError",
    "Base",
    "DatabaseError",
    "NotFoundError",
    "Settings",
    "ToolHandlerError",
    "ToolHandlerNotFoundError",
    "ToolNotFoundError",
    "ValidationError",
    "get_session",
    "get_settings",
    "init_db",
]

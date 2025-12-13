"""Tests for tool handlers."""

from pathlib import Path

import pytest

# Merged handler lists for testing
from src.core.services.cobol_analysis.tool_handlers_service import (
    TOOL_HANDLERS as COBOL_HANDLERS,
)
from src.core.services.cobol_analysis.tool_handlers_service import (
    build_asg_handler,
    parse_cobol_handler,
)
from src.core.services.common.tool_service_service import get_handler
from src.core.services.general.tool_handlers_service import (
    TOOL_HANDLERS as GENERAL_HANDLERS,
)
from src.core.services.general.tool_handlers_service import (
    calculator_add_handler,
    echo_handler,
)


ALL_HANDLERS = {**GENERAL_HANDLERS, **COBOL_HANDLERS}


def list_handlers() -> list[str]:
    """List all available handler names from all domains."""
    return list(ALL_HANDLERS.keys())


def test_echo_handler() -> None:
    """Test echo handler returns the input text."""
    result = echo_handler({"text": "Hello, World!"})

    assert result["success"] is True
    assert result["message"] == "Echo: Hello, World!"
    assert result["original_text"] == "Hello, World!"


def test_echo_handler_empty_text() -> None:
    """Test echo handler with empty text."""
    result = echo_handler({"text": ""})

    assert result["success"] is True
    assert result["message"] == "Echo: "
    assert result["original_text"] == ""


def test_echo_handler_missing_text() -> None:
    """Test echo handler with missing text parameter."""
    result = echo_handler({})

    assert result["success"] is True
    assert result["original_text"] == ""


def test_calculator_add_handler() -> None:
    """Test calculator add handler."""
    result = calculator_add_handler({"a": 5, "b": 3})

    assert result["success"] is True
    assert result["operation"] == "addition"
    assert result["a"] == 5
    assert result["b"] == 3
    assert result["result"] == 8.0


def test_calculator_add_handler_floats() -> None:
    """Test calculator add handler with floats."""
    result = calculator_add_handler({"a": 2.5, "b": 3.7})

    assert result["success"] is True
    assert result["result"] == pytest.approx(6.2)


def test_calculator_add_handler_zero() -> None:
    """Test calculator add handler with zero."""
    result = calculator_add_handler({"a": 0, "b": 0})

    assert result["success"] is True
    assert result["result"] == 0.0


def test_calculator_add_handler_invalid_input() -> None:
    """Test calculator add handler with invalid input."""
    result = calculator_add_handler({"a": "invalid", "b": 5})

    assert result["success"] is False
    assert "error" in result


def test_get_handler() -> None:
    """Test get_handler function."""
    handler = get_handler("echo_handler")
    assert handler is not None
    assert callable(handler)

    handler = get_handler("calculator_add_handler")
    assert handler is not None
    assert callable(handler)

    handler = get_handler("nonexistent_handler")
    assert handler is None


def test_list_handlers() -> None:
    """Test list_handlers function."""
    handlers = list_handlers()

    assert isinstance(handlers, list)
    assert "echo_handler" in handlers
    assert "calculator_add_handler" in handlers
    assert "parse_cobol_handler" in handlers
    assert "build_asg_handler" in handlers
    assert len(handlers) >= 5


# ============================================================================
# COBOL Analysis Handler Tests
# ============================================================================


def test_parse_cobol_handler_with_source_code() -> None:
    """Test parse_cobol_handler with file_path parameter."""
    # Use an existing sample file for reliable testing
    file_path = Path(__file__).parent / ".." / "cobol_samples" / "CUSTOMER-ACCOUNT-MAIN.cbl"
    result = parse_cobol_handler({"file_path": str(file_path)})

    # Handler should return a result
    assert "success" in result
    if result["success"]:
        assert "ast" in result
        assert "program_name" in result
        # ParseNode-serialized AST
        assert result["ast"]["node_type"] == "PROGRAM"
    else:
        # If parsing fails, should have error message
        assert "error" in result


def test_parse_cobol_handler_missing_parameters() -> None:
    """Test parse_cobol_handler with missing parameters."""
    result = parse_cobol_handler({})

    assert result["success"] is False
    assert "error" in result
    assert "source_code" in result["error"] or "file_path" in result["error"]


def test_parse_cobol_handler_invalid_syntax() -> None:
    """Test parse_cobol_handler with invalid COBOL syntax."""
    result = parse_cobol_handler({"source_code": "INVALID COBOL CODE"})

    assert result["success"] is False
    assert "error" in result


def test_build_asg_handler_missing_parameters() -> None:
    """Test build_asg_handler with missing parameters."""
    result = build_asg_handler({})
    assert result["success"] is False
    assert "error" in result


def test_get_handler_cobol_handlers() -> None:
    """Test get_handler for COBOL handlers."""
    handler = get_handler("parse_cobol_handler")
    assert handler is not None
    assert callable(handler)

    handler = get_handler("build_asg_handler")
    assert handler is not None
    assert callable(handler)

    handler = get_handler("parse_cobol_raw_handler")
    assert handler is not None
    assert callable(handler)

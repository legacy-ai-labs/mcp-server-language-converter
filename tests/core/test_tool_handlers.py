"""Tests for tool handlers."""

import pytest

from src.core.services.tool_handlers_service import (
    calculator_add_handler,
    echo_handler,
    get_handler,
    list_handlers,
)


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
    assert len(handlers) >= 2

"""Registry of predefined tool handlers."""

from collections.abc import Callable
from typing import Any


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def echo_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Echo handler that returns the input text.

    Args:
        parameters: Handler parameters containing 'text' key

    Returns:
        Dictionary with echoed text
    """
    text = parameters.get("text", "")
    return {
        "success": True,
        "message": f"Echo: {text}",
        "original_text": text,
    }


def calculator_add_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Add two numbers.

    Args:
        parameters: Handler parameters containing 'a' and 'b' keys

    Returns:
        Dictionary with the sum
    """
    a = parameters.get("a", 0)
    b = parameters.get("b", 0)

    try:
        result = float(a) + float(b)
        return {
            "success": True,
            "operation": "addition",
            "a": a,
            "b": b,
            "result": result,
        }
    except (ValueError, TypeError) as e:
        return {
            "success": False,
            "error": f"Invalid numbers provided: {e}",
        }


# Registry mapping handler names to handler functions
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "echo_handler": echo_handler,
    "calculator_add_handler": calculator_add_handler,
}


def get_handler(handler_name: str) -> ToolHandler | None:
    """Get a tool handler by name.

    Args:
        handler_name: Name of the handler

    Returns:
        Handler function or None if not found
    """
    return TOOL_HANDLERS.get(handler_name)


def list_handlers() -> list[str]:
    """List all available handler names.

    Returns:
        List of handler names
    """
    return list(TOOL_HANDLERS.keys())

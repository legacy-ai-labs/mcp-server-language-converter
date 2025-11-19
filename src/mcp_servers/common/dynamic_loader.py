"""Dynamic tool loading from database.

This module provides generic tool loading functionality that works across all
domain-specific MCP servers. Tools are loaded from the database and registered
with FastMCP at server startup.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from src.core.database import async_session_factory
from src.core.repositories.tool_repository import ToolRepository
from src.core.services.observability_service import trace_tool_execution
from src.core.services.tool_handlers_service import TOOL_HANDLERS


logger = logging.getLogger(__name__)


def _create_traced_tool(
    tool_name: str,
    domain: str,
    transport: str,
    tool_func: Any,
) -> Any:
    """Create a tool function with observability tracing.

    Args:
        tool_name: Name of the tool
        domain: Domain the tool belongs to
        transport: Transport protocol
        tool_func: Async function that calls the handler

    Returns:
        Tool function with tracing
    """

    async def traced_tool(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Tool wrapper with observability."""
        # Build parameters dict from args/kwargs for tracing
        parameters = kwargs.copy() if kwargs else {}
        if args:
            # For tools with positional args, map them appropriately
            param_names = list(tool_func.__code__.co_varnames[: tool_func.__code__.co_argcount])
            param_names = [p for p in param_names if p != "self"]
            for idx, arg in enumerate(args):
                if idx < len(param_names):
                    parameters[param_names[idx]] = arg

        async with trace_tool_execution(
            tool_name=tool_name,
            parameters=parameters,
            domain=domain,
            transport=transport,
        ) as trace_ctx:
            try:
                result = await tool_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                trace_ctx["status"] = "error"
                trace_ctx["error_type"] = type(e).__name__
                trace_ctx["error_message"] = str(e)
                return {"success": False, "error": str(e)}
            trace_ctx["output_data"] = result
            if not isinstance(result, dict):
                logger.warning(
                    f"Tool {tool_name} returned non-dict result: {type(result).__name__}"
                )
                return {
                    "success": False,
                    "error": f"Tool returned invalid type: {type(result).__name__}",
                }
            return result

    return traced_tool


def _create_echo_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create echo tool wrapper."""

    async def tool_impl(text: str) -> dict[str, Any]:
        result = handler_func({"text": text})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def echo_tool(text: str) -> dict[str, Any]:
        """Echo back the provided text."""
        result = await traced(text)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return echo_tool


def _create_calculator_add_tool(
    handler_func: Any, tool_name: str, domain: str, transport: str
) -> Any:
    """Create calculator_add tool wrapper."""

    async def tool_impl(a: float, b: float) -> dict[str, Any]:
        result = handler_func({"a": a, "b": b})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def calculator_add_tool(a: float, b: float) -> dict[str, Any]:
        """Add two numbers together."""
        result = await traced(a, b)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return calculator_add_tool


def _create_parse_cobol_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create parse_cobol tool wrapper."""

    async def tool_impl(
        source_code: str | None = None, file_path: str | None = None
    ) -> dict[str, Any]:
        result = handler_func({"source_code": source_code, "file_path": file_path})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def parse_cobol_tool(
        source_code: str | None = None, file_path: str | None = None
    ) -> dict[str, Any]:
        """Parse COBOL source code into AST."""
        result = await traced(source_code, file_path)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return parse_cobol_tool


def _create_parse_cobol_raw_tool(
    handler_func: Any, tool_name: str, domain: str, transport: str
) -> Any:
    """Create parse_cobol_raw tool wrapper."""

    async def tool_impl(
        source_code: str | None = None, file_path: str | None = None
    ) -> dict[str, Any]:
        result = handler_func({"source_code": source_code, "file_path": file_path})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def parse_cobol_raw_tool(
        source_code: str | None = None, file_path: str | None = None
    ) -> dict[str, Any]:
        """Parse COBOL source code into raw ParseNode (parse tree)."""
        result = await traced(source_code, file_path)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return parse_cobol_raw_tool


def _create_build_ast_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create build_ast tool wrapper."""

    async def tool_impl(parse_tree: dict[str, Any]) -> dict[str, Any]:
        result = handler_func({"parse_tree": parse_tree})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def build_ast_tool(parse_tree: dict[str, Any]) -> dict[str, Any]:
        """Build Abstract Syntax Tree (AST) from ParseNode."""
        result = await traced(parse_tree)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return build_ast_tool


def _create_build_cfg_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create build_cfg tool wrapper."""

    async def tool_impl(ast: dict[str, Any]) -> dict[str, Any]:
        result = handler_func({"ast": ast})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def build_cfg_tool(ast: dict[str, Any]) -> dict[str, Any]:
        """Build Control Flow Graph (CFG) from AST."""
        result = await traced(ast)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return build_cfg_tool


def _create_build_dfg_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create build_dfg tool wrapper."""

    async def tool_impl(ast: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        result = handler_func({"ast": ast, "cfg": cfg})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def build_dfg_tool(ast: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        """Build Data Flow Graph (DFG) from AST + CFG."""
        result = await traced(ast, cfg)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return build_dfg_tool


def _create_build_pdg_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create build_pdg tool wrapper."""

    async def tool_impl(
        ast: dict[str, Any], cfg: dict[str, Any], dfg: dict[str, Any]
    ) -> dict[str, Any]:
        result = handler_func({"ast": ast, "cfg": cfg, "dfg": dfg})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def build_pdg_tool(
        ast: dict[str, Any], cfg: dict[str, Any], dfg: dict[str, Any]
    ) -> dict[str, Any]:
        """Build Program Dependency Graph (PDG) from AST + CFG + DFG.

        The PDG combines control dependencies (from CFG) and data dependencies
        (from DFG) into a unified graph showing all program dependencies.
        """
        result = await traced(ast, cfg, dfg)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return build_pdg_tool


def _create_generic_tool(handler_func: Any, tool_name: str, domain: str, transport: str) -> Any:
    """Create generic tool wrapper."""

    async def tool_impl(text: str = "") -> dict[str, Any]:
        result = handler_func({"text": text})
        if not isinstance(result, dict):
            logger.warning(
                f"Handler for {tool_name} returned non-dict result: {type(result).__name__}"
            )
            return {
                "success": False,
                "error": f"Handler returned invalid type: {type(result).__name__}",
            }
        return result

    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)

    async def generic_tool_wrapper(text: str = "") -> dict[str, Any]:
        """Generic wrapper for unknown tools."""
        result = await traced(text)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid type: {type(result).__name__}",
            }
        return result

    return generic_tool_wrapper


async def load_tools_from_database(mcp: FastMCP, domain: str, transport: str = "stdio") -> None:
    """Load active tools for a specific domain from database and register with FastMCP.

    Args:
        mcp: FastMCP server instance to register tools with
        domain: Domain to filter tools by (e.g., "general", "kubernetes")
        transport: Transport protocol being used (stdio, http, rest)

    Raises:
        Exception: If tool loading fails
    """
    try:
        async with async_session_factory() as session:
            tool_repo = ToolRepository(session)

            # Get active tools for this domain
            active_tools = await tool_repo.get_by_domain(domain)

            logger.info(f"Loading {len(active_tools)} tools for domain '{domain}'...")

            for tool in active_tools:
                try:
                    await register_tool_from_db(mcp, tool, domain, transport)
                    logger.info(f"Registered tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to register tool {tool.name}: {e}")

    except Exception as e:
        logger.error(f"Failed to load tools from database: {e}")
        raise


async def register_tool_from_db(mcp: FastMCP, tool: Any, domain: str, transport: str) -> None:
    """Register a single tool from database record with observability tracing.

    This creates tool-specific wrappers with proper signatures instead of
    using **kwargs which FastMCP doesn't support. Each wrapper includes
    automatic tracing for observability.

    Args:
        mcp: FastMCP server instance
        tool: Tool database record with name, description, and handler_name
        domain: Domain the tool belongs to (for metrics)
        transport: Transport protocol (stdio, http, rest) for metrics

    Raises:
        ValueError: If handler function not found in registry
    """
    handler_func = TOOL_HANDLERS.get(tool.handler_name)
    if not handler_func:
        raise ValueError(f"Handler {tool.handler_name} not found for tool {tool.name}")

    if tool.name == "echo":
        tool_func = _create_echo_tool(handler_func, tool.name, domain, transport)
    elif tool.name == "calculator_add":
        tool_func = _create_calculator_add_tool(handler_func, tool.name, domain, transport)
    elif tool.name == "parse_cobol":
        tool_func = _create_parse_cobol_tool(handler_func, tool.name, domain, transport)
    elif tool.name == "parse_cobol_raw":
        tool_func = _create_parse_cobol_raw_tool(handler_func, tool.name, domain, transport)
    elif tool.name == "build_ast":
        tool_func = _create_build_ast_tool(handler_func, tool.name, domain, transport)
    elif tool.name == "build_cfg":
        tool_func = _create_build_cfg_tool(handler_func, tool.name, domain, transport)
    elif tool.name == "build_dfg":
        tool_func = _create_build_dfg_tool(handler_func, tool.name, domain, transport)
    elif tool.name == "build_pdg":
        tool_func = _create_build_pdg_tool(handler_func, tool.name, domain, transport)
    else:
        tool_func = _create_generic_tool(handler_func, tool.name, domain, transport)

    decorated_tool = mcp.tool(name=tool.name, description=tool.description)(tool_func)

    if not hasattr(mcp, "_dynamic_tools"):
        mcp._dynamic_tools = []  # type: ignore[attr-defined]
    mcp._dynamic_tools.append(decorated_tool)  # type: ignore[attr-defined]

"""Seed initial tools into the database."""

import asyncio
import logging

from src.core.database import async_session_factory
from src.core.schemas.tool_schema import ToolCreate
from src.core.services.common.tool_service_service import ToolService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


INITIAL_TOOLS = [
    ToolCreate(
        name="echo",
        description="Echo back the provided text. Useful for testing and simple text repetition.",
        handler_name="echo_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to echo back",
                }
            },
            "required": ["text"],
        },
        category="utility",
        domain="general",
        is_active=True,
    ),
    ToolCreate(
        name="calculator_add",
        description="Add two numbers together. Performs simple addition operation.",
        handler_name="calculator_add_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number to add",
                },
                "b": {
                    "type": "number",
                    "description": "Second number to add",
                },
            },
            "required": ["a", "b"],
        },
        category="calculation",
        domain="general",
        is_active=True,
    ),
    ToolCreate(
        name="parse_cobol",
        description="Parse COBOL source code into Abstract Syntax Tree (AST)",
        handler_name="parse_cobol_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "source_code": {
                    "type": "string",
                    "description": "COBOL source code",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to COBOL file",
                },
            },
            "required": [],
        },
        category="parsing",
        domain="cobol_analysis",
        is_active=True,
    ),
    ToolCreate(
        name="parse_cobol_raw",
        description="Parse COBOL source code into raw ParseNode (parse tree) without building AST",
        handler_name="parse_cobol_raw_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "source_code": {
                    "type": "string",
                    "description": "COBOL source code",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to COBOL file",
                },
            },
            "required": [],
        },
        category="parsing",
        domain="cobol_analysis",
        is_active=True,
    ),
    ToolCreate(
        name="build_ast",
        description="Build Abstract Syntax Tree (AST) from ParseNode",
        handler_name="build_ast_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "parse_tree": {
                    "type": "object",
                    "description": "ParseNode representation (from parse_cobol)",
                },
            },
            "required": ["parse_tree"],
        },
        category="parsing",
        domain="cobol_analysis",
        is_active=True,
    ),
    ToolCreate(
        name="build_cfg",
        description="Build Control Flow Graph (CFG) from AST",
        handler_name="build_cfg_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "ast": {
                    "type": "object",
                    "description": "AST representation",
                },
            },
            "required": ["ast"],
        },
        category="parsing",
        domain="cobol_analysis",
        is_active=True,
    ),
    ToolCreate(
        name="build_dfg",
        description="Build Data Flow Graph (DFG) from AST + CFG",
        handler_name="build_dfg_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "ast": {
                    "type": "object",
                    "description": "AST representation",
                },
                "cfg": {
                    "type": "object",
                    "description": "CFG representation",
                },
            },
            "required": ["ast", "cfg"],
        },
        category="parsing",
        domain="cobol_analysis",
        is_active=True,
    ),
    ToolCreate(
        name="build_pdg",
        description="Build Program Dependency Graph (PDG) from AST + CFG + DFG. Combines control dependencies (from CFG) and data dependencies (from DFG) into a unified graph.",
        handler_name="build_pdg_handler",
        parameters_schema={
            "type": "object",
            "properties": {
                "ast": {
                    "type": "object",
                    "description": "AST representation (ProgramNode)",
                },
                "cfg": {
                    "type": "object",
                    "description": "Control Flow Graph representation",
                },
                "dfg": {
                    "type": "object",
                    "description": "Data Flow Graph representation",
                },
            },
            "required": ["ast", "cfg", "dfg"],
        },
        category="parsing",
        domain="cobol_analysis",
        is_active=True,
    ),
]


async def seed_tools() -> None:
    """Seed initial tools into the database."""
    logger.info(f"Seeding {len(INITIAL_TOOLS)} tools...")

    for tool_data in INITIAL_TOOLS:
        # Use a new session for each tool to avoid transaction issues
        async with async_session_factory() as session:
            service = ToolService(session)
            try:
                # Check if tool already exists
                existing_tool = await service.get_tool_by_name(tool_data.name)
                logger.info(f"Tool '{tool_data.name}' already exists (ID: {existing_tool.id})")
                continue
            except Exception:  # nosec B110
                # Tool doesn't exist, proceed with creation
                pass

            try:
                # Create tool
                tool = await service.create_tool(tool_data)
                logger.info(f"Created tool: {tool.name} (ID: {tool.id})")
            except Exception as e:
                logger.error(f"Failed to create tool '{tool_data.name}': {e}")

    logger.info("Tool seeding complete!")


async def main() -> None:
    """Main function to run seeding."""
    await seed_tools()


if __name__ == "__main__":
    asyncio.run(main())

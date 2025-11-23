"""Tool definitions for COBOL analysis domain using decorator-based registration."""

from typing import Any

from src.core.services.cobol_analysis.tool_handlers_service import (
    batch_analyze_cobol_directory_handler,
    build_ast_handler,
    build_cfg_handler,
    build_dfg_handler,
    build_pdg_handler,
    parse_cobol_handler,
    parse_cobol_raw_handler,
)
from src.mcp_servers.common.base_server import create_mcp_server
from src.mcp_servers.common.tool_registry import register_tool


# Create FastMCP instance for this domain
mcp = create_mcp_server(domain="cobol_analysis")


@register_tool(
    domain="cobol_analysis",
    tool_name="parse_cobol",
    description="Parse COBOL source code into Abstract Syntax Tree (AST)",
)
async def parse_cobol(
    source_code: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Parse COBOL source code into Abstract Syntax Tree (AST).

    Parses COBOL source code and builds an AST representation suitable for analysis.
    Supports both direct source code input and file path references.

    Args:
        source_code: COBOL source code as a string (optional if file_path provided)
        file_path: Path to COBOL source file (optional if source_code provided)

    Returns:
        Dictionary with success status, AST data, and metadata
    """
    return parse_cobol_handler({"source_code": source_code, "file_path": file_path})


@register_tool(
    domain="cobol_analysis",
    tool_name="parse_cobol_raw",
    description="Parse COBOL source code into raw ParseNode (parse tree)",
)
async def parse_cobol_raw(
    source_code: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Parse COBOL source code into raw ParseNode (parse tree) without building AST.

    Returns the raw parse tree structure from the COBOL parser without AST transformation.
    Useful for low-level analysis or debugging parser issues.

    Args:
        source_code: COBOL source code as a string (optional if file_path provided)
        file_path: Path to COBOL source file (optional if source_code provided)

    Returns:
        Dictionary with success status and raw parse tree data
    """
    return parse_cobol_raw_handler({"source_code": source_code, "file_path": file_path})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_ast",
    description="Build Abstract Syntax Tree (AST) from ParseNode",
)
async def build_ast(parse_tree: dict[str, Any]) -> dict[str, Any]:
    """Build Abstract Syntax Tree (AST) from ParseNode.

    Transforms a raw parse tree into a structured AST representation.
    The AST provides a higher-level, semantically meaningful representation
    of the COBOL program structure.

    Args:
        parse_tree: Raw parse tree data from parse_cobol_raw

    Returns:
        Dictionary with success status and AST data
    """
    return build_ast_handler({"parse_tree": parse_tree})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_cfg",
    description="Build Control Flow Graph (CFG) from AST",
)
async def build_cfg(ast: dict[str, Any]) -> dict[str, Any]:
    """Build Control Flow Graph (CFG) from AST.

    Generates a control flow graph showing the execution paths through the program.
    The CFG is essential for understanding program flow, identifying dead code,
    and analyzing conditional logic.

    Args:
        ast: Abstract Syntax Tree data from parse_cobol or build_ast

    Returns:
        Dictionary with success status, CFG nodes, edges, and metadata
    """
    return build_cfg_handler({"ast": ast})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_dfg",
    description="Build Data Flow Graph (DFG) from AST and CFG",
)
async def build_dfg(ast: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Build Data Flow Graph (DFG) from AST and CFG.

    Analyzes data dependencies and variable usage throughout the program.
    The DFG tracks how data flows between statements, which is crucial for
    understanding variable dependencies and potential data-related bugs.

    Args:
        ast: Abstract Syntax Tree data
        cfg: Control Flow Graph data from build_cfg

    Returns:
        Dictionary with success status, DFG edges, and data flow analysis
    """
    return build_dfg_handler({"ast": ast, "cfg": cfg})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_pdg",
    description="Build Program Dependency Graph (PDG) from AST, CFG, and DFG",
)
async def build_pdg(
    ast: dict[str, Any],
    cfg: dict[str, Any],
    dfg: dict[str, Any],
) -> dict[str, Any]:
    """Build Program Dependency Graph (PDG) from AST, CFG, and DFG.

    Combines control flow and data flow information into a unified dependency graph.
    The PDG is the most comprehensive representation, showing both control and data
    dependencies, enabling advanced program analysis like slicing and refactoring.

    Args:
        ast: Abstract Syntax Tree data
        cfg: Control Flow Graph data
        dfg: Data Flow Graph data from build_dfg

    Returns:
        Dictionary with success status, PDG structure, and dependency information
    """
    return build_pdg_handler({"ast": ast, "cfg": cfg, "dfg": dfg})


@register_tool(
    domain="cobol_analysis",
    tool_name="batch_analyze_cobol_directory",
    description="Batch analyze all COBOL files in a directory and subdirectories",
)
async def batch_analyze_cobol_directory(
    directory_path: str,
    file_extensions: list[str] | None = None,
    output_directory: str | None = None,
) -> dict[str, Any]:
    """Batch analyze all COBOL files in a directory and its subdirectories.

    For each COBOL file found, this tool will:
    1. Parse the file to generate AST
    2. Build Control Flow Graph (CFG)
    3. Build Data Flow Graph (DFG)
    4. Build Program Dependency Graph (PDG)
    5. Save all results to JSON files

    This is useful for analyzing large COBOL codebases, generating comprehensive
    documentation, or preparing data for migration/modernization projects.

    Args:
        directory_path: Root directory to scan for COBOL files
        file_extensions: Optional list of file extensions to search for
                        (default: ['.cbl', '.cob', '.cobol'])
        output_directory: Optional output directory for results
                         (default: tests/cobol_samples/result)

    Returns:
        Dictionary with batch processing summary including:
        - Total files found and processed
        - Success/failure counts
        - Per-file results with stage-by-stage status
        - Paths to all saved analysis files
    """
    parameters: dict[str, Any] = {"directory_path": directory_path}
    if file_extensions is not None:
        parameters["file_extensions"] = file_extensions
    if output_directory is not None:
        parameters["output_directory"] = output_directory
    return batch_analyze_cobol_directory_handler(parameters)

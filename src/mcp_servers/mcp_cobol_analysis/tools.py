"""Tool definitions for COBOL analysis domain using decorator-based registration."""

from typing import Any

from src.core.services.cobol_analysis.tool_handlers_service import (
    analyze_copybook_usage_handler,
    analyze_data_flow_handler,
    analyze_program_system_handler,
    batch_analyze_cobol_directory_handler,
    build_ast_handler,
    build_call_graph_handler,
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


@register_tool(
    domain="cobol_analysis",
    tool_name="analyze_program_system",
    description="Analyze relationships across multiple COBOL programs to build a system graph",
)
async def analyze_program_system(
    directory_path: str,
    file_extensions: list[str] | None = None,
    include_inactive: bool = False,
    max_depth: int | None = None,
) -> dict[str, Any]:
    """Analyze relationships across multiple COBOL programs to build a system-level graph.

    This tool performs comprehensive inter-program analysis to identify:
    - CALL relationships between programs
    - Shared COPYBOOK/COPY dependencies
    - Data flow through parameters (BY VALUE/REFERENCE)
    - Program entry/exit points
    - External file dependencies

    The result is a complete system graph showing how all COBOL programs
    in a codebase are interconnected, which is essential for:
    - Impact analysis when modifying programs
    - Understanding system architecture
    - Identifying dead code
    - Planning modernization efforts

    Args:
        directory_path: Root directory containing COBOL files
        file_extensions: Optional list of extensions (default: ['.cbl', '.cob', '.cobol'])
        include_inactive: Include commented-out relationships (default: False)
        max_depth: Maximum directory depth to scan (default: None for unlimited)

    Returns:
        Dictionary containing:
        - programs: Dictionary of program metadata
        - call_graph: Call relationships between programs
        - copybook_usage: Copybook dependency matrix
        - data_flows: Parameter flow information
        - system_metrics: Overall system complexity metrics
        - entry_points: Programs that are never called
        - isolated_programs: Programs with no dependencies
    """
    parameters: dict[str, Any] = {
        "directory_path": directory_path,
        "include_inactive": include_inactive,
    }
    if file_extensions is not None:
        parameters["file_extensions"] = file_extensions
    if max_depth is not None:
        parameters["max_depth"] = max_depth
    return analyze_program_system_handler(parameters)


@register_tool(
    domain="cobol_analysis",
    tool_name="build_call_graph",
    description="Build a call graph showing CALL relationships between COBOL programs",
)
async def build_call_graph(
    programs: dict[str, Any],
    call_graph: dict[str, Any] | None = None,
    output_format: str = "dict",
    include_metrics: bool = True,
) -> dict[str, Any]:
    """Build a call graph showing CALL relationships between COBOL programs.

    This tool creates a directed graph of program calls, useful for:
    - Understanding program dependencies
    - Identifying entry points and dead code
    - Impact analysis for changes
    - Detecting circular dependencies

    The graph can be output in multiple formats for visualization or further analysis.

    Args:
        programs: Dictionary of program information from analyze_program_system
        call_graph: Optional raw call relationships (extracted from programs if not provided)
        output_format: Graph format - "dict", "dot" (Graphviz), "mermaid" (default: "dict")
        include_metrics: Include graph metrics like cycles and components (default: True)

    Returns:
        Dictionary containing:
        - nodes: List of program nodes with attributes
        - edges: List of call edges with attributes
        - metrics: Graph-level metrics (cycles, components, density)
        - visualization: Graph in requested format (if dot/mermaid)
    """
    parameters: dict[str, Any] = {
        "programs": programs,
        "output_format": output_format,
        "include_metrics": include_metrics,
    }
    if call_graph is not None:
        parameters["call_graph"] = call_graph
    return build_call_graph_handler(parameters)


@register_tool(
    domain="cobol_analysis",
    tool_name="analyze_copybook_usage",
    description="Analyze COPYBOOK usage patterns across COBOL programs",
)
async def analyze_copybook_usage(
    copybook_usage: dict[str, Any],
    programs: dict[str, Any] | None = None,
    include_recommendations: bool = True,
) -> dict[str, Any]:
    """Analyze COPYBOOK usage patterns across COBOL programs.

    This tool identifies:
    - Which programs use which copybooks
    - Shared copybook dependencies
    - Copybook impact analysis (which programs affected by copybook changes)
    - Most frequently used copybooks
    - Potential optimization opportunities

    Understanding copybook usage is critical for:
    - Assessing change impact when modifying shared copybooks
    - Identifying consolidation opportunities
    - Managing technical debt
    - Planning data structure modernization

    Args:
        copybook_usage: Dictionary of copybook -> programs mapping from analyze_program_system
        programs: Optional program information for enhanced analysis
        include_recommendations: Generate optimization recommendations (default: True)

    Returns:
        Dictionary containing:
        - copybooks: List of copybook analysis records
        - usage_matrix: Programs vs copybooks matrix
        - impact_analysis: Programs affected by each copybook
        - recommendations: Suggested optimizations (if enabled)
        - statistics: Summary metrics
    """
    parameters: dict[str, Any] = {
        "copybook_usage": copybook_usage,
        "include_recommendations": include_recommendations,
    }
    if programs is not None:
        parameters["programs"] = programs
    return analyze_copybook_usage_handler(parameters)


@register_tool(
    domain="cobol_analysis",
    tool_name="analyze_data_flow",
    description="Analyze data flow through program parameters (BY VALUE/REFERENCE)",
)
async def analyze_data_flow(
    data_flows: list[dict[str, Any]],
    programs: dict[str, Any] | None = None,
    trace_variable: str | None = None,
) -> dict[str, Any]:
    """Analyze data flow through program parameters (BY VALUE/REFERENCE).

    This tool tracks how data flows between programs through CALL parameters,
    identifying:
    - Parameter passing patterns (BY VALUE vs BY REFERENCE)
    - Data dependencies between programs
    - Potential data integrity issues
    - Parameter type mismatches

    Data flow analysis is essential for:
    - Understanding data dependencies
    - Detecting potential side effects
    - Planning data structure changes
    - Ensuring data integrity during refactoring

    Args:
        data_flows: List of data flow records from analyze_program_system
        programs: Optional program information for enhanced analysis
        trace_variable: Optional specific variable to trace through the system

    Returns:
        Dictionary containing:
        - flows: Analyzed data flow records
        - chains: Data flow chains showing multi-hop flows
        - warnings: Potential issues detected (mismatches, excessive parameters)
        - variable_usage: Usage patterns for traced variables
        - by_reference_summary: Summary of BY REFERENCE usage
        - statistics: Summary metrics
    """
    parameters: dict[str, Any] = {"data_flows": data_flows}
    if programs is not None:
        parameters["programs"] = programs
    if trace_variable is not None:
        parameters["trace_variable"] = trace_variable
    return analyze_data_flow_handler(parameters)

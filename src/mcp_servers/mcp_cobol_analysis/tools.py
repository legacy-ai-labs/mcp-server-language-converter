"""Tool definitions for COBOL analysis domain using decorator-based registration."""

from typing import Any

from src.core.services.cobol_analysis.tool_handlers_service import (
    analyze_copybook_usage_handler,
    analyze_data_flow_handler,
    analyze_program_system_handler,
    batch_analyze_cobol_directory_handler,
    batch_resolve_copybooks_handler,
    build_asg_handler,
    build_call_graph_handler,
    parse_cobol_handler,
    parse_cobol_raw_handler,
    prepare_cobol_for_antlr_handler,
    resolve_copybooks_handler,
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
    tool_name="build_asg",
    description="Build Abstract Semantic Graph (ASG) using ProLeap COBOL Parser",
)
async def build_asg(
    file_path: str | None = None,
    source_code: str | None = None,
    program_name: str | None = None,
    copybook_dir: str | None = None,
    include_summary: bool = True,
    include_call_graph: bool = True,
    include_data_refs: bool = False,
) -> dict[str, Any]:
    """Build Abstract Semantic Graph (ASG) using ProLeap COBOL Parser.

    The ASG provides semantic information beyond what the AST offers, including:
    - Program structure with resolved references
    - Data definitions with all clause types (PICTURE, USAGE, VALUE, OCCURS, REDEFINES, etc.)
    - Cross-references showing which statements use each data item
    - Procedure statements with full details
    - CALL/PERFORM statement targets and parameters

    This tool uses the ProLeap COBOL Parser (Java) to generate a comprehensive
    semantic representation of the COBOL program. ProLeap must be set up first
    by running: uv run python scripts/proleap_full_asg_export.py <any_cobol_file>

    Args:
        file_path: Path to COBOL source file (optional if source_code provided)
        source_code: COBOL source code as string (optional if file_path provided)
        program_name: Program name when using source_code (default: "UNNAMED")
        copybook_dir: Optional path to copybook directory for COPY resolution
        include_summary: Include summary statistics (default: True)
        include_call_graph: Include call graph extraction (default: True)
        include_data_refs: Include data item cross-references (default: False)

    Returns:
        Dictionary containing:
        - success: Whether ASG generation succeeded
        - asg: Full ASG structure with compilation units, divisions, sections
        - source_file: Source file path
        - proleap_version: ProLeap parser version used
        - export_type: Export format type
        - summary: ASG summary with counts (if include_summary=True)
        - call_graph: Call graph nodes and edges (if include_call_graph=True)
        - data_references: Cross-reference data (if include_data_refs=True)
        - saved_to: Path where result was saved

    Example:
        # Build ASG from file
        result = await build_asg(file_path="programs/CUSTOMER-MGMT.cbl")

        if result['success']:
            print(f"Programs: {len(result['asg']['compilation_units'])}")
            print(f"Call targets: {result['summary']['compilation_units'][0]['call_targets']}")

        # Build ASG with all analyses
        result = await build_asg(
            file_path="programs/MAIN-BATCH.cbl",
            copybook_dir="copybooks/",
            include_data_refs=True
        )
    """
    parameters: dict[str, Any] = {
        "include_summary": include_summary,
        "include_call_graph": include_call_graph,
        "include_data_refs": include_data_refs,
    }
    if file_path is not None:
        parameters["file_path"] = file_path
    if source_code is not None:
        parameters["source_code"] = source_code
    if program_name is not None:
        parameters["program_name"] = program_name
    if copybook_dir is not None:
        parameters["copybook_dir"] = copybook_dir
    return build_asg_handler(parameters)


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


@register_tool(
    domain="cobol_analysis",
    tool_name="prepare_cobol_for_antlr",
    description="Prepare COBOL source for ANTLR parser by removing unsupported optional paragraphs (AUTHOR, DATE-WRITTEN, etc.)",
)
async def prepare_cobol_for_antlr(
    source_code: str | None = None,
    source_file: str | None = None,
    output_file: str | None = None,
) -> dict[str, Any]:
    """Prepare COBOL source for ANTLR parser by removing unsupported optional paragraphs.

    The ANTLR Cobol85.g4 grammar doesn't support optional IDENTIFICATION DIVISION
    paragraphs like AUTHOR, DATE-WRITTEN, DATE-COMPILED, INSTALLATION, SECURITY,
    and REMARKS. This tool removes them to make files compatible with the parser.

    This is typically the first preprocessing step before parsing COBOL files.

    Args:
        source_code: COBOL source code as string (optional if source_file provided)
        source_file: Path to COBOL source file (optional if source_code provided)
        output_file: Optional path to save cleaned file

    Returns:
        Dictionary containing:
        - success: Whether cleaning succeeded
        - cleaned_source: COBOL source with optional paragraphs removed
        - paragraphs_removed: List of paragraph types that were removed
        - output_file: Path to saved file (if requested)

    Example:
        # Clean a file before parsing
        result = await prepare_cobol_for_antlr(
            source_file="programs/ACCOUNT-VALIDATOR.cbl",
            output_file="programs/ACCOUNT-VALIDATOR-CLEAN.cbl"
        )

        if result['success']:
            print(f"Removed paragraphs: {result['paragraphs_removed']}")
            # Now parse the cleaned source
            parse_result = await parse_cobol(source_code=result['cleaned_source'])
    """
    parameters: dict[str, Any] = {}
    if source_code is not None:
        parameters["source_code"] = source_code
    if source_file is not None:
        parameters["source_file"] = source_file
    if output_file is not None:
        parameters["output_file"] = output_file
    return prepare_cobol_for_antlr_handler(parameters)


@register_tool(
    domain="cobol_analysis",
    tool_name="resolve_copybooks",
    description="Resolve COPY statements by replacing them with actual copybook content (COBOL preprocessor)",
)
async def resolve_copybooks(
    source_file: str,
    copybook_paths: list[str],
    output_file: str | None = None,
    keep_markers: bool = True,
) -> dict[str, Any]:
    """Resolve COPY/COPYBOOK statements by replacing them with actual copybook content.

    This tool acts as a COBOL preprocessor that expands all COPY statements,
    generating a new "flattened" file with all copybooks inlined. This is essential
    for parsing COBOL files that use copybooks, as most parsers cannot resolve
    COPY statements.

    The resolved file can then be parsed, analyzed, or compiled without requiring
    access to the original copybook files.

    Args:
        source_file: Path to COBOL source file with COPY statements
        copybook_paths: List of directories to search for copybooks
        output_file: Optional path to save resolved file (if not provided, returns content only)
        keep_markers: Add comment markers showing copybook boundaries (default: True)

    Returns:
        Dictionary containing:
        - success: Whether resolution succeeded
        - resolved_source: Complete source with COPY statements expanded
        - copybooks_resolved: List of copybooks that were successfully resolved
        - copybooks_missing: List of copybooks that couldn't be found
        - output_file: Path to saved file (if requested)
        - line_mapping: Original line -> expanded line mapping
        - original_lines: Number of lines in original file
        - expanded_lines: Number of lines in expanded file

    Example:
        # Resolve copybooks for a single file
        result = await resolve_copybooks(
            source_file="programs/MAIN-BATCH.cbl",
            copybook_paths=["copybooks/", "lib/"],
            output_file="programs/MAIN-BATCH-RESOLVED.cbl"
        )

        if result['success']:
            print(f"Resolved {result['total_copybooks']} copybooks")
            # Now parse the resolved file
            parse_result = await parse_cobol(source_code=result['resolved_source'])
    """
    parameters: dict[str, Any] = {
        "source_file": source_file,
        "copybook_paths": copybook_paths,
        "keep_markers": keep_markers,
    }
    if output_file is not None:
        parameters["output_file"] = output_file
    return resolve_copybooks_handler(parameters)


@register_tool(
    domain="cobol_analysis",
    tool_name="batch_resolve_copybooks",
    description="Batch resolve COPY statements for all COBOL files in a directory, renaming originals to .original",
)
async def batch_resolve_copybooks(
    directory: str,
    copybook_paths: list[str],
    file_extensions: list[str] | None = None,
    recursive: bool = False,
    keep_markers: bool = True,
    backup_originals: bool = True,
) -> dict[str, Any]:
    """Batch resolve COPY statements for all COBOL files in a directory.

    This tool processes entire directories of COBOL files, expanding all COPY statements
    and optionally renaming the originals to .original extension. This is the recommended
    way to prepare a COBOL codebase for parsing and analysis.

    Workflow:
    1. Finds all COBOL files with COPY statements in the directory
    2. Resolves copybooks by inserting actual content
    3. Renames originals to .original extension (if backup_originals=True)
    4. Saves resolved files with the original names

    Benefits of .original strategy:
    - Prevents re-processing the same files
    - Preserves original files for reference
    - Resolved files become the new "main" files for parsing

    Args:
        directory: Directory containing COBOL files to process
        copybook_paths: List of directories to search for copybooks
        file_extensions: List of extensions to process (default: ['.cbl', '.cob', '.cobol'])
        recursive: Search subdirectories (default: False)
        keep_markers: Add copybook boundary markers (default: True)
        backup_originals: Rename originals to .original (default: True)

    Returns:
        Dictionary containing:
        - success: Whether batch processing succeeded
        - files_processed: List of successfully processed files with details
        - files_failed: List of files that failed with error messages
        - summary: Processing summary with totals and statistics

    Example:
        # Process all COBOL files in a directory
        result = await batch_resolve_copybooks(
            directory="programs/",
            copybook_paths=["copybooks/", "lib/copybooks/"],
            backup_originals=True  # Rename to .original
        )

        print(f"Processed {result['summary']['files_processed']} files")
        print(f"Resolved {result['summary']['total_copybooks_resolved']} copybooks")

        # Now you can parse all the resolved files without COPY statements
        for file_info in result['files_processed']:
            parse_result = await parse_cobol(file_path=file_info['file'])
    """
    parameters: dict[str, Any] = {
        "directory": directory,
        "copybook_paths": copybook_paths,
        "recursive": recursive,
        "keep_markers": keep_markers,
        "backup_originals": backup_originals,
    }
    if file_extensions is not None:
        parameters["file_extensions"] = file_extensions
    return batch_resolve_copybooks_handler(parameters)

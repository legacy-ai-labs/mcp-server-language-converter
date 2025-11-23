"""COBOL Analysis MCP Tools - Decorator-based tool registration."""
from typing import Any

from src.core.services.cobol_analysis.tool_handlers_service import (
    analyze_copybook_usage_handler,
    analyze_data_flow_handler,
    analyze_program_system_handler,
    build_call_graph_handler,
)
from src.mcp_servers.common.base_server import mcp
from src.mcp_servers.common.tool_registry import register_tool


@register_tool(
    domain="cobol_analysis",
    tool_name="analyze_program_system",
    description="Analyze COBOL program system to identify relationships, dependencies, and architecture",
)
@mcp.tool()
async def analyze_program_system(
    directory_path: str, file_extensions: list[str] | None = None, include_inactive: bool = False
) -> dict[str, Any]:
    """Analyze a system of COBOL programs to identify relationships and dependencies.

    This tool scans a directory of COBOL programs and builds a complete picture of:
    - Program call relationships (who calls whom)
    - Copybook usage and sharing patterns
    - Entry points and isolated programs
    - Data flow through parameters
    - Potential circular dependencies

    Args:
        directory_path: Path to directory containing COBOL programs
        file_extensions: List of file extensions to include (e.g., [".cbl", ".cob"])
        include_inactive: Whether to include inactive/commented programs

    Returns:
        Dictionary containing:
        - programs: Details about each program
        - call_graph: Program call relationships
        - copybook_usage: Which programs use which copybooks
        - data_flows: Parameter passing between programs
        - entry_points: Programs that are not called by others
        - isolated_programs: Programs with no relationships
        - system_metrics: Overall statistics
    """
    return analyze_program_system_handler(
        {
            "directory_path": directory_path,
            "file_extensions": file_extensions or [".cbl", ".cob"],
            "include_inactive": include_inactive,
        }
    )


@register_tool(
    domain="cobol_analysis",
    tool_name="build_call_graph",
    description="Build a call graph visualization from analyzed COBOL programs",
)
@mcp.tool()
async def build_call_graph(
    programs: dict[str, Any],
    call_graph: dict[str, list[str]],
    output_format: str = "dict",
    include_metrics: bool = True,
) -> dict[str, Any]:
    """Build a call graph from analyzed program data.

    Creates a visual representation of program call relationships in various formats.
    Detects circular dependencies and calculates graph metrics.

    Args:
        programs: Program data from analyze_program_system
        call_graph: Call relationships from analyze_program_system
        output_format: Format for output - "dict", "dot", or "mermaid"
        include_metrics: Whether to include graph analysis metrics

    Returns:
        Dictionary containing:
        - graph: The call graph in requested format
        - visualization: Text representation (for dot/mermaid)
        - metrics: Graph statistics if include_metrics=True
          - total_nodes: Number of programs
          - total_edges: Number of call relationships
          - has_cycles: Whether circular dependencies exist
          - cycles: List of circular dependency chains
    """
    return build_call_graph_handler(
        {
            "programs": programs,
            "call_graph": call_graph,
            "output_format": output_format,
            "include_metrics": include_metrics,
        }
    )


@register_tool(
    domain="cobol_analysis",
    tool_name="analyze_copybook_usage",
    description="Analyze how copybooks are used across COBOL programs",
)
@mcp.tool()
async def analyze_copybook_usage(
    copybook_usage: dict[str, list[str]],
    programs: dict[str, Any],
    include_recommendations: bool = True,
) -> dict[str, Any]:
    """Analyze copybook usage patterns across programs.

    Identifies shared copybooks, single-use copybooks, and provides recommendations
    for consolidation or refactoring.

    Args:
        copybook_usage: Copybook usage data from analyze_program_system
        programs: Program data from analyze_program_system
        include_recommendations: Whether to include refactoring recommendations

    Returns:
        Dictionary containing:
        - copybooks: List of copybooks with usage details
        - statistics: Usage statistics
          - total_copybooks: Number of unique copybooks
          - total_relationships: Total usage instances
          - shared_count: Copybooks used by multiple programs
          - average_usage: Average uses per copybook
        - recommendations: Suggested improvements (if requested)
    """
    return analyze_copybook_usage_handler(
        {
            "copybook_usage": copybook_usage,
            "programs": programs,
            "include_recommendations": include_recommendations,
        }
    )


@register_tool(
    domain="cobol_analysis",
    tool_name="analyze_data_flow",
    description="Analyze data flow through parameters between COBOL programs",
)
@mcp.tool()
async def analyze_data_flow(
    data_flows: list[dict[str, Any]], programs: dict[str, Any], trace_variable: str | None = None
) -> dict[str, Any]:
    """Analyze how data flows between programs through parameters.

    Traces parameter passing, identifies BY REFERENCE vs BY VALUE usage,
    and detects potential data sharing issues.

    Args:
        data_flows: Data flow information from analyze_program_system
        programs: Program data from analyze_program_system
        trace_variable: Optional variable name to trace through the system

    Returns:
        Dictionary containing:
        - flows: List of data flows with details
        - statistics: Flow statistics
          - total_flows: Number of program-to-program flows
          - total_parameters: Total parameters passed
          - by_reference_flows: Flows using BY REFERENCE
          - unique_variables: Distinct variables passed
        - warnings: Potential issues detected
        - variable_trace: Path of specific variable (if trace_variable provided)
    """
    return analyze_data_flow_handler(
        {"data_flows": data_flows, "programs": programs, "trace_variable": trace_variable}
    )

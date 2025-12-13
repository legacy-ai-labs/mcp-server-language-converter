"""Registry of COBOL analysis tool handlers."""

import json
import logging
import re
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.models.cobol_asg_model import (
    Program,
    ReferenceResolver,
    ResolutionStatus,
    SymbolTable,
)
from src.core.models.complexity_metrics_model import (
    AnalysisLevel,
    ASGMetrics,
    CFGMetrics,
    ComplexityMetrics,
    ControlFlowMetrics,
    DataMetrics,
    DependencyMetrics,
    DFGMetrics,
    LineMetrics,
    StructuralMetrics,
)
from src.core.services.cobol_analysis.asg_builder_service import (
    ASGBuilderError,
    build_asg_from_file,
    build_asg_from_source,
)
from src.core.services.cobol_analysis.cfg_builder_service import (
    CFGBuilderError,
    ControlFlowGraph,
    build_cfg_from_ast,
    serialize_cfg,
)
from src.core.services.cobol_analysis.cobol_parser_antlr_service import (
    Comment,
    ParseNode,
    parse_cobol,
    parse_cobol_file,
    parse_cobol_file_with_copybooks,
    parse_cobol_with_copybooks,
)
from src.core.services.cobol_analysis.dfg_builder_service import (
    DataFlowGraph,
    DFGBuilderError,
    build_dfg_from_ast,
    serialize_dfg,
)


logger = logging.getLogger(__name__)


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


# ============================================================================
# Metadata extraction helper (works with ParseNode)
# ============================================================================


def _extract_program_name_from_parse_tree(parse_tree: ParseNode) -> str | None:
    """Extract program name from parse tree.

    Args:
        parse_tree: The ParseNode tree

    Returns:
        Program name or None if not found
    """

    def find_node(node: ParseNode, target_type: str) -> ParseNode | None:
        if target_type in {node.type, node.rule_name}:
            return node
        for child in node.children:
            result = find_node(child, target_type)
            if result:
                return result
        return None

    # Try to find PROGRAM_NAME or programIdParagraph
    program_name_node = find_node(parse_tree, "PROGRAM_NAME")
    if program_name_node and program_name_node.value:
        return str(program_name_node.value)

    # Try finding in programIdParagraph
    program_id_node = find_node(parse_tree, "programIdParagraph")
    if program_id_node:
        # Look for the program name in children
        for child in program_id_node.children:
            if "programName" in {child.type, child.rule_name}:
                if child.value:
                    return str(child.value)
                # Get text from terminal children
                for terminal in child.children:
                    if terminal.text:
                        return terminal.text
    return None


def _extract_metadata_from_parse_tree(
    parse_tree: ParseNode, file_path: str | None = None
) -> dict[str, Any]:
    """Extract basic metadata from parse tree.

    Args:
        parse_tree: The ParseNode tree
        file_path: Optional source file path

    Returns:
        Dictionary with program_info and basic metrics
    """
    program_name = _extract_program_name_from_parse_tree(parse_tree)

    return {
        "program_info": {
            "program_id": program_name,
            "file_path": file_path,
        },
        "dependencies": {
            "calls": [],
            "copybooks": [],
            "files": [],
        },
    }


# ============================================================================
# Result persistence helper
# ============================================================================


def _save_tool_result(
    tool_name: str,
    result: dict[str, Any],
    source_identifier: str | None = None,
) -> Path | None:
    """Save tool execution result to tests/cobol_samples/result directory.

    Args:
        tool_name: Name of the tool (e.g., "parse_cobol", "build_cfg")
        result: Tool execution result dictionary
        source_identifier: Optional identifier for the source (e.g., program name, file path)

    Returns:
        Path to the saved file, or None if save failed
    """
    try:
        # Create result directory if it doesn't exist
        result_dir = Path("tests/cobol_samples/result")
        result_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        identifier = source_identifier or "unknown"
        # Sanitize identifier for filename
        identifier = "".join(c if c.isalnum() or c in "-_" else "_" for c in identifier)
        filename = f"{tool_name}_{identifier}_{timestamp}.json"
        filepath = result_dir / filename

        # Save result as JSON
        with filepath.open("w") as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"Saved {tool_name} result to {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save {tool_name} result: {e}")
        return None


def _deserialize_parse_node(node_dict: dict[str, Any]) -> ParseNode:
    """Deserialize ParseNode from dict.

    Args:
        node_dict: Dictionary representation of ParseNode

    Returns:
        ParseNode instance
    """
    # Support both old format (node_type) and new format (type)
    node_type = node_dict.get("type") or node_dict.get("node_type", "")
    value = node_dict.get("value")
    children = node_dict.get("children", [])

    # Recursively deserialize children
    deserialized_children: list[ParseNode] = []
    for child in children:
        if isinstance(child, dict):
            deserialized_children.append(_deserialize_parse_node(child))

    # Build ParseNode with new Pydantic model structure
    return ParseNode(
        type=node_type,
        children=deserialized_children,
        value=value,
        # Support both old and new location fields
        start_line=node_dict.get("start_line") or node_dict.get("line_number"),
        start_column=node_dict.get("start_column") or node_dict.get("column_number"),
        end_line=node_dict.get("end_line"),
        end_column=node_dict.get("end_column"),
        # Extended fields for full AST representation
        id=node_dict.get("id"),
        rule_index=node_dict.get("rule_index"),
        rule_name=node_dict.get("rule_name"),
        text=node_dict.get("text"),
        token_type=node_dict.get("token_type"),
        token_name=node_dict.get("token_name"),
    )


def _serialize_parse_node(node: ParseNode) -> dict[str, Any]:
    """Serialize ParseNode to dict.

    Args:
        node: ParseNode instance to serialize

    Returns:
        Dictionary representation of ParseNode (uses Pydantic model_dump)
    """
    # Use Pydantic's model_dump for serialization
    # exclude_none=True to avoid cluttering output with None values
    return node.model_dump(exclude_none=True)


def _resolve_copybook_paths(
    *,
    copybook_directories: Any,
    file_path: str | None,
) -> list[Path] | None:
    """Resolve copybook directories from explicit input or auto-detection.

    Args:
        copybook_directories: Optional list of directory strings
        file_path: Optional COBOL file path (used for auto-detection)

    Returns:
        List of copybook directories as Path objects, or None.
    """
    if copybook_directories:
        return [Path(d) for d in copybook_directories]

    if not file_path:
        return None

    file_dir = Path(file_path).parent
    candidates: list[Path] = [file_dir]

    # Check common copybook directory names in same and sibling directories
    for name in ["copybooks", "copy", "copybook", "COPYBOOKS", "COPY"]:
        for base in [file_dir, file_dir.parent]:
            candidate = base / name
            if candidate.exists():
                candidates.append(candidate)

    # De-duplicate while preserving order
    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)

    return unique_candidates


def _parse_cobol_source_or_file(
    *,
    source_code: str | None,
    file_path: str | None,
    copybook_paths: list[Path] | None,
) -> tuple[ParseNode, list[Comment], Any, Any | None]:
    """Parse COBOL from either file or source, optionally with copybook preprocessing.

    Returns:
        parsed_tree, comments, id_metadata, preprocessed (or None)
    """
    if file_path:
        if copybook_paths:
            parsed_tree, comments, id_metadata, preprocessed = parse_cobol_file_with_copybooks(
                file_path, copybook_paths
            )
            return parsed_tree, comments, id_metadata, preprocessed

        parsed_tree, comments, id_metadata = parse_cobol_file(file_path)
        return parsed_tree, comments, id_metadata, None

    if source_code is None:
        raise ValueError("Either 'source_code' or 'file_path' must be provided")

    if copybook_paths:
        parsed_tree, comments, id_metadata, preprocessed = parse_cobol_with_copybooks(
            source_code, copybook_paths
        )
        return parsed_tree, comments, id_metadata, preprocessed

    parsed_tree, comments, id_metadata = parse_cobol(source_code)
    return parsed_tree, comments, id_metadata, None


def _add_copybook_info_to_metadata(metadata: dict[str, Any], preprocessed: Any | None) -> None:
    """Attach copybook preprocessing info to metadata if available."""
    if not preprocessed:
        return

    metadata["copybook_info"] = {
        "copybooks_found": len(preprocessed.copybook_usages),
        "copybooks": [
            {
                "name": usage.copybook_name,
                "resolved": usage.is_resolved,
                "resolved_path": str(usage.resolved_path) if usage.resolved_path else None,
            }
            for usage in preprocessed.copybook_usages
        ],
        "unresolved": preprocessed.unresolved_copybooks,
    }


# ============================================================================
# COBOL Analysis Tool Handlers
# ============================================================================


def parse_cobol_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Parse COBOL source code into AST (Abstract Syntax Tree).

    The ParseNode structure serves as the AST for COBOL analysis.
    This provides a unified structure for further analysis (ASG, user stories, call graphs).

    Args:
        parameters: Handler parameters containing:
            - 'source_code' or 'file_path': The COBOL source to parse
            - 'copybook_directories': Optional list of directories to search for copybooks

    Returns:
        Dictionary with AST (ParseNode) representation
    """
    source_code = parameters.get("source_code")
    file_path = parameters.get("file_path")
    copybook_directories = parameters.get("copybook_directories")

    if not source_code and not file_path:
        return {
            "success": False,
            "error": "Either 'source_code' or 'file_path' must be provided",
        }

    try:
        if source_code is not None and not isinstance(source_code, str):
            return {
                "success": False,
                "error": "'source_code' must be a string",
            }

        if file_path is not None and not isinstance(file_path, str):
            return {
                "success": False,
                "error": "'file_path' must be a string",
            }

        copybook_paths = _resolve_copybook_paths(
            copybook_directories=copybook_directories,
            file_path=file_path if isinstance(file_path, str) else None,
        )

        parsed_tree, _comments, _id_metadata, preprocessed = _parse_cobol_source_or_file(
            source_code=source_code if isinstance(source_code, str) else None,
            file_path=file_path if isinstance(file_path, str) else None,
            copybook_paths=copybook_paths,
        )

        # ParseNode is now the AST - serialize using Pydantic
        ast_dict = _serialize_parse_node(parsed_tree)

        # Extract program name from parse tree
        program_name = _extract_program_name_from_parse_tree(parsed_tree)

        # Extract metadata from parse tree
        metadata = _extract_metadata_from_parse_tree(parsed_tree, file_path)

        _add_copybook_info_to_metadata(metadata, preprocessed)

        result: dict[str, Any] = {
            "success": True,
            "ast": ast_dict,
            "program_name": program_name,
            "metadata": metadata,
        }

        # Save result to file
        saved_path = _save_tool_result("parse_cobol", result, program_name)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to parse COBOL")
        return {
            "success": False,
            "error": str(e),
        }


def parse_cobol_raw_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Parse COBOL source code into raw ParseNode (parse tree).

    This tool returns the raw parse tree without building the AST.
    Use this when you want to inspect the parse tree or build the AST separately.

    Args:
        parameters: Handler parameters containing 'source_code' or 'file_path'

    Returns:
        Dictionary with ParseNode representation
    """
    source_code = parameters.get("source_code")
    file_path = parameters.get("file_path")

    if not source_code and not file_path:
        return {
            "success": False,
            "error": "Either 'source_code' or 'file_path' must be provided",
        }

    try:
        if file_path:
            parse_node, _, _ = parse_cobol_file(file_path)
        else:
            if not isinstance(source_code, str):
                return {
                    "success": False,
                    "error": "'source_code' must be a string",
                }
            parse_node, _, _ = parse_cobol(source_code)
        parse_tree_dict = _serialize_parse_node(parse_node)

        result = {
            "success": True,
            "parse_tree": parse_tree_dict,
            "node_type": parse_node.node_type,
        }

        # Save result to file
        identifier = Path(file_path).stem if file_path else "source_code"
        saved_path = _save_tool_result("parse_cobol_raw", result, identifier)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to parse COBOL")
        return {
            "success": False,
            "error": str(e),
        }


def build_asg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build Abstract Semantic Graph (ASG) from COBOL source.

    This handler uses the pure Python ASG builder that works directly with the
    ANTLR parse tree. It produces Pydantic models that capture:
    - Program structure with all divisions
    - Data definitions with clause types (PICTURE, USAGE, VALUE, OCCURS, etc.)
    - Procedure statements with full details
    - CALL/PERFORM statement targets and parameters
    - Level 88 conditions

    Args:
        parameters: Handler parameters containing either:
            - 'file_path': Path to COBOL file
            - 'source_code': COBOL source code string

    Returns:
        Dictionary with ASG representation as serialized Pydantic model
    """
    file_path = parameters.get("file_path")
    source_code = parameters.get("source_code")

    if not file_path and not source_code:
        return {"success": False, "error": "Either 'file_path' or 'source_code' is required"}

    try:
        # Build ASG using pure Python builder
        if file_path:
            asg = build_asg_from_file(str(file_path))
            program_name = Path(file_path).stem
        else:
            # source_code is guaranteed non-None here due to earlier check
            assert source_code is not None  # nosec B101
            asg = build_asg_from_source(source_code)
            # Extract program name from ASG
            program_name = "UNNAMED"
            if asg.compilation_units:
                cu = asg.compilation_units[0]
                if cu.program_units:
                    pu = cu.program_units[0]
                    if pu.identification_division and pu.identification_division.program_id:
                        program_name = pu.identification_division.program_id

        # Convert Pydantic model to dict for JSON serialization
        asg_dict = asg.model_dump(mode="json", exclude_none=True)

        result: dict[str, Any] = {
            "success": True,
            "asg": asg_dict,
            "source_file": asg.source_file,
            "builder": "python",
            "compilation_unit_count": len(asg.compilation_units),
            "external_calls": list(asg.external_calls),
        }

        # Add summary information
        if asg.compilation_units:
            cu = asg.compilation_units[0]
            if cu.program_units:
                pu = cu.program_units[0]
                result["summary"] = {
                    "program_id": pu.identification_division.program_id
                    if pu.identification_division
                    else None,
                    "has_data_division": pu.data_division is not None,
                    "has_procedure_division": pu.procedure_division is not None,
                }

                if pu.data_division:
                    dd = pu.data_division
                    result["summary"]["working_storage_entries"] = (
                        len(dd.working_storage.entries) if dd.working_storage else 0
                    )
                    result["summary"]["linkage_entries"] = (
                        len(dd.linkage_section.entries) if dd.linkage_section else 0
                    )

                if pu.procedure_division:
                    pd = pu.procedure_division
                    result["summary"]["paragraph_count"] = len(pd.paragraphs)
                    result["summary"]["call_statement_count"] = len(pd.call_statements)
                    result["summary"]["using_parameters"] = pd.using_parameters

        # Save result to file
        saved_path = _save_tool_result("build_asg", result, program_name)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result

    except ASGBuilderError as e:
        logger.warning(f"ASG build failed: {e}")
        return {"success": False, "error": str(e)}
    except SyntaxError as e:
        logger.warning(f"COBOL syntax error: {e}")
        return {"success": False, "error": f"COBOL syntax error: {e}"}
    except Exception as e:
        logger.exception("Failed to build ASG")
        return {"success": False, "error": str(e)}


def build_ast_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912
    """Build Abstract Syntax Tree (AST) from COBOL source code.

    This handler parses COBOL source code and returns a structured AST
    representation using ParseNode. The AST captures the syntactic structure
    of the COBOL program including:
    - Program divisions (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)
    - Sections and paragraphs
    - Statements and expressions
    - Data definitions with levels and clauses
    - Source location information for each node

    The AST is suitable for:
    - Code analysis and transformation
    - Documentation generation
    - Migration planning
    - Further semantic analysis (ASG building)

    Args:
        parameters: Handler parameters containing:
            - 'source_code': COBOL source code as string (optional if file_path provided)
            - 'file_path': Path to COBOL source file (optional if source_code provided)
            - 'include_comments': Include extracted comments (default: True)
            - 'include_metadata': Include identification metadata (default: True)
            - 'copybook_directories': Optional list of directories to search for copybooks

    Returns:
        Dictionary with AST representation including:
        - success: Whether parsing succeeded
        - ast: Complete AST structure as nested dictionary
        - program_name: Extracted program name
        - comments: List of extracted comments (if include_comments=True)
        - metadata: Identification metadata like AUTHOR, DATE-WRITTEN (if include_metadata=True)
        - node_count: Total number of nodes in the AST
        - saved_to: Path where result was saved
    """
    source_code = parameters.get("source_code")
    file_path = parameters.get("file_path")
    include_comments = parameters.get("include_comments", True)
    include_metadata = parameters.get("include_metadata", True)
    copybook_directories = parameters.get("copybook_directories")

    if not source_code and not file_path:
        return {
            "success": False,
            "error": "Either 'source_code' or 'file_path' must be provided",
        }

    try:
        # Validate inputs
        if source_code is not None and not isinstance(source_code, str):
            return {
                "success": False,
                "error": "'source_code' must be a string",
            }

        if file_path is not None and not isinstance(file_path, str):
            return {
                "success": False,
                "error": "'file_path' must be a string",
            }

        # Resolve copybook paths if needed
        copybook_paths = _resolve_copybook_paths(
            copybook_directories=copybook_directories,
            file_path=file_path if isinstance(file_path, str) else None,
        )

        # Parse COBOL source
        parsed_tree, comments, id_metadata, preprocessed = _parse_cobol_source_or_file(
            source_code=source_code if isinstance(source_code, str) else None,
            file_path=file_path if isinstance(file_path, str) else None,
            copybook_paths=copybook_paths,
        )

        # Serialize AST using Pydantic
        ast_dict = _serialize_parse_node(parsed_tree)

        # Extract program name
        program_name = _extract_program_name_from_parse_tree(parsed_tree)

        # Count nodes in the AST
        def count_nodes(node: dict[str, Any]) -> int:
            count = 1
            for child in node.get("children", []):
                count += count_nodes(child)
            return count

        node_count = count_nodes(ast_dict)

        # Build result
        result: dict[str, Any] = {
            "success": True,
            "ast": ast_dict,
            "program_name": program_name,
            "node_count": node_count,
            "root_type": parsed_tree.type,
        }

        # Include comments if requested
        if include_comments and comments:
            result["comments"] = [
                {
                    "text": comment.text,
                    "line": comment.location.line,
                    "type": comment.comment_type.value,
                }
                for comment in comments
            ]
            result["comment_count"] = len(comments)

        # Include metadata if requested
        if include_metadata:
            metadata_dict: dict[str, Any] = {}
            if id_metadata.author:
                metadata_dict["author"] = id_metadata.author
            if id_metadata.installation:
                metadata_dict["installation"] = id_metadata.installation
            if id_metadata.date_written:
                metadata_dict["date_written"] = id_metadata.date_written
            if id_metadata.date_compiled:
                metadata_dict["date_compiled"] = id_metadata.date_compiled
            if id_metadata.security:
                metadata_dict["security"] = id_metadata.security
            if id_metadata.remarks:
                metadata_dict["remarks"] = id_metadata.remarks
            if metadata_dict:
                result["identification_metadata"] = metadata_dict

        # Add copybook info if available
        _add_copybook_info_to_metadata(result, preprocessed)

        # Add source file info
        if file_path:
            result["source_file"] = file_path

        # Save result to file
        saved_path = _save_tool_result("build_ast", result, program_name or "unknown")
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result

    except SyntaxError as e:
        logger.warning(f"COBOL syntax error: {e}")
        return {
            "success": False,
            "error": f"COBOL syntax error: {e}",
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e),
        }
    except Exception as e:
        logger.exception("Failed to build AST")
        return {
            "success": False,
            "error": str(e),
        }


def _process_single_cobol_file(cobol_file: Path) -> dict[str, Any]:
    """Process a single COBOL file through analysis stages.

    Parses the COBOL source into AST (ParseNode) and optionally builds the ASG.

    Args:
        cobol_file: Path to the COBOL file to process

    Returns:
        Dictionary with processing results for this file
    """
    file_result: dict[str, Any] = {
        "file_path": str(cobol_file),
        "success": False,
        "stages": {},
    }

    logger.info(f"Processing {cobol_file}")

    # Stage 1: Parse COBOL to AST (ParseNode)
    parse_result = parse_cobol_handler({"file_path": str(cobol_file)})
    file_result["stages"]["parse"] = {
        "success": parse_result.get("success", False),
        "saved_to": parse_result.get("saved_to"),
    }

    if not parse_result.get("success"):
        file_result["error"] = f"Parse failed: {parse_result.get('error', 'Unknown error')}"
        return file_result

    program_name = parse_result.get("program_name", "unknown")

    # Stage 2: Build ASG (semantic analysis)
    asg_result = build_asg_handler({"file_path": str(cobol_file)})
    file_result["stages"]["asg"] = {
        "success": asg_result.get("success", False),
        "saved_to": asg_result.get("saved_to"),
    }

    if not asg_result.get("success"):
        # ASG failure is not fatal - parsing succeeded
        logger.warning(f"ASG build failed for {cobol_file}: {asg_result.get('error')}")

    # All stages succeeded (parsing is the minimum requirement)
    file_result["success"] = True
    file_result["program_name"] = program_name
    return file_result


def _find_cobol_files(root_path: Path, file_extensions: list[str]) -> list[Path]:
    """Find all COBOL files in directory and subdirectories.

    Args:
        root_path: Root directory to search
        file_extensions: List of file extensions to search for

    Returns:
        List of paths to COBOL files found
    """
    cobol_files: list[Path] = []
    for ext in file_extensions:
        cobol_files.extend(root_path.rglob(f"*{ext}"))
    return cobol_files


def _save_batch_summary(summary: dict[str, Any], output_path: Path) -> dict[str, Any]:
    """Save batch processing summary to JSON file.

    Args:
        summary: Summary dictionary to save
        output_path: Directory to save summary file in

    Returns:
        Updated summary with saved file path
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    summary_file = output_path / f"batch_summary_{timestamp}.json"
    with summary_file.open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    summary["summary_saved_to"] = str(summary_file)
    return summary


def batch_analyze_cobol_directory_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Batch analyze all COBOL files in a directory and its subdirectories.

    For each COBOL file found, this handler will:
    1. Parse the file to generate AST
    2. Build Control Flow Graph (CFG)
    3. Build Data Flow Graph (DFG)
    4. Build Program Dependency Graph (PDG)
    5. Save all results to JSON files

    Args:
        parameters: Handler parameters containing:
            - directory_path: Root directory to scan for COBOL files
            - file_extensions: Optional list of extensions (default: ['.cbl', '.cob', '.cobol'])
            - output_directory: Optional output dir for results (default: tests/cobol_samples/result)

    Returns:
        Dictionary with batch processing summary
    """
    directory_path = parameters.get("directory_path")
    file_extensions = parameters.get("file_extensions", [".cbl", ".cob", ".cobol"])
    output_directory = parameters.get("output_directory", "tests/cobol_samples/result")

    if not directory_path:
        return {"success": False, "error": "directory_path is required"}

    try:
        root_path = Path(directory_path)
        if not root_path.exists():
            return {"success": False, "error": f"Directory not found: {directory_path}"}

        if not root_path.is_dir():
            return {"success": False, "error": f"Path is not a directory: {directory_path}"}

        # Ensure output directory exists
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all COBOL files
        cobol_files = _find_cobol_files(root_path, file_extensions)

        if not cobol_files:
            return {
                "success": True,
                "message": f"No COBOL files found in {directory_path}",
                "files_processed": 0,
                "files_succeeded": 0,
                "files_failed": 0,
                "results": [],
            }

        logger.info(f"Found {len(cobol_files)} COBOL files to process")

        # Process each file
        results = []
        files_succeeded = 0
        files_failed = 0

        for cobol_file in cobol_files:
            try:
                file_result = _process_single_cobol_file(cobol_file)
                if file_result["success"]:
                    files_succeeded += 1
                else:
                    files_failed += 1
                results.append(file_result)
            except Exception as e:
                logger.exception(f"Failed to process {cobol_file}")
                results.append(
                    {
                        "file_path": str(cobol_file),
                        "success": False,
                        "error": str(e),
                        "stages": {},
                    }
                )
                files_failed += 1

        # Create and save summary
        summary = {
            "success": True,
            "directory": str(root_path),
            "files_found": len(cobol_files),
            "files_processed": len(results),
            "files_succeeded": files_succeeded,
            "files_failed": files_failed,
            "output_directory": str(output_path),
            "results": results,
        }

        summary = _save_batch_summary(summary, output_path)

        logger.info(
            f"Batch processing complete: {files_succeeded} succeeded, {files_failed} failed"
        )

        return summary

    except Exception as e:
        logger.exception("Batch processing failed")
        return {"success": False, "error": str(e)}


def analyze_program_system_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912
    """Analyze relationships across multiple COBOL programs to build a system-level graph.

    This tool performs comprehensive inter-program analysis to identify:
    - CALL relationships between programs
    - Shared COPYBOOK/COPY dependencies
    - Data flow through parameters (BY VALUE/REFERENCE)
    - Program entry/exit points
    - External file dependencies

    Args:
        parameters: Dictionary with:
            - directory_path: Root directory containing COBOL files
            - file_extensions: Optional list of extensions (default: ['.cbl', '.cob', '.cobol'])
            - include_inactive: Include commented-out relationships (default: False)
            - max_depth: Maximum directory depth to scan (default: None for unlimited)

    Returns:
        Dictionary containing:
            - programs: List of program metadata
            - call_graph: Call relationships between programs
            - copybook_usage: Copybook dependency matrix
            - data_flows: Parameter flow information
            - system_metrics: Overall system complexity metrics
    """
    try:
        # Extract parameters
        directory_path = parameters.get("directory_path")
        if not directory_path:
            return {
                "success": False,
                "error": "directory_path is required",
            }

        directory = Path(directory_path)
        if not directory.exists():
            return {
                "success": False,
                "error": f"Directory not found: {directory_path}",
            }

        file_extensions = parameters.get("file_extensions", [".cbl", ".cob", ".cobol"])
        # include_inactive: When implemented, this will control whether to analyze
        # commented-out code (e.g., CALL statements or COPY dependencies in comment lines).
        # This is useful for identifying legacy dependencies, temporarily disabled code,
        # or understanding the historical evolution of program relationships.
        # Currently not implemented - all analysis ignores commented code.
        # include_inactive = parameters.get("include_inactive", False)
        max_depth = parameters.get("max_depth")

        # Data structures for system analysis
        programs = {}  # program_id -> program_info
        call_graph = defaultdict(list)  # caller -> list of callees
        copybook_usage = defaultdict(set)  # copybook -> set of programs using it
        data_flows = []  # List of parameter flow records
        external_files = defaultdict(set)  # file -> set of programs using it

        # Find all COBOL files
        pattern = "**/*" if max_depth is None else "*" * min(max_depth, 10) + "/*"
        cobol_files: list[Path] = []
        for ext in file_extensions:
            cobol_files.extend(directory.glob(f"{pattern}{ext}"))

        if not cobol_files:
            return {
                "success": True,
                "warning": f"No COBOL files found in {directory_path}",
                "programs": [],
                "call_graph": {},
                "copybook_usage": {},
                "data_flows": [],
                "system_metrics": {},
            }

        # Analyze each COBOL file
        for file_path in cobol_files:
            try:
                # Parse the file
                parse_result = parse_cobol_handler({"file_path": str(file_path)})

                if not parse_result.get("success"):
                    continue

                # ast = parse_result.get("ast")  # Reserved for future AST analysis
                metadata = parse_result.get("metadata", {})

                # Extract program ID
                program_id = metadata.get("program_info", {}).get("program_id")
                if not program_id:
                    # Try to extract from filename if not in metadata
                    program_id = file_path.stem.upper()

                # Store program information
                programs[program_id] = {
                    "file_path": str(file_path),
                    "program_id": program_id,
                    "size_metrics": metadata.get("size_metrics", {}),
                    "dependencies": [],
                    "callers": [],
                    "callees": [],
                    "copybooks": [],
                    "external_files": [],
                }

                # Extract dependencies from metadata
                dependencies = metadata.get("dependencies", {})

                # Process CALL statements
                for call in dependencies.get("calls", []):
                    called_program = call.get("target")
                    if called_program:
                        call_graph[program_id].append(called_program)
                        programs[program_id]["callees"].append(called_program)

                        # Track parameter flow
                        if call.get("parameters"):
                            data_flows.append(
                                {
                                    "from": program_id,
                                    "to": called_program,
                                    "parameters": call.get("parameters"),
                                    "type": "CALL",
                                }
                            )

                # Process COPY statements
                for copybook in dependencies.get("copybooks", []):
                    copybook_name = copybook.get("name")
                    if copybook_name:
                        copybook_usage[copybook_name].add(program_id)
                        programs[program_id]["copybooks"].append(copybook_name)

                # Process file references
                for file_ref in dependencies.get("files", []):
                    file_name = file_ref.get("name")
                    if file_name:
                        external_files[file_name].add(program_id)
                        programs[program_id]["external_files"].append(file_name)

            except Exception as e:
                # Log error but continue processing other files
                logger.warning(f"Error analyzing {file_path}: {e}")
                continue

        # Build reverse call graph (callers)
        for caller, callees in call_graph.items():
            for callee in callees:
                if callee in programs:
                    programs[callee]["callers"].append(caller)

        # Calculate system metrics
        total_programs = len(programs)
        total_calls = sum(len(callees) for callees in call_graph.values())
        total_copybooks = len(copybook_usage)

        # Identify isolated programs (no calls in or out)
        isolated_programs = [
            pid for pid, info in programs.items() if not info["callers"] and not info["callees"]
        ]

        # Identify entry points (called by no one)
        entry_points = [
            pid for pid, info in programs.items() if not info["callers"] and info["callees"]
        ]

        # Calculate complexity metrics
        max_fan_out = max((len(info["callees"]) for info in programs.values()), default=0)
        max_fan_in = max((len(info["callers"]) for info in programs.values()), default=0)

        system_metrics = {
            "total_programs": total_programs,
            "total_relationships": total_calls,
            "total_copybooks": total_copybooks,
            "total_external_files": len(external_files),
            "isolated_programs": len(isolated_programs),
            "entry_points": len(entry_points),
            "max_fan_out": max_fan_out,
            "max_fan_in": max_fan_in,
            "average_dependencies": total_calls / total_programs if total_programs > 0 else 0,
        }

        return {
            "success": True,
            "programs": programs,
            "call_graph": {k: list(v) for k, v in call_graph.items()},
            "copybook_usage": {k: list(v) for k, v in copybook_usage.items()},
            "data_flows": data_flows,
            "external_files": {k: list(v) for k, v in external_files.items()},
            "system_metrics": system_metrics,
            "entry_points": entry_points,
            "isolated_programs": isolated_programs,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"System analysis failed: {e!s}",
        }


def build_call_graph_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0915
    """Build a call graph showing CALL relationships between COBOL programs.

    This tool creates a directed graph of program calls, useful for:
    - Understanding program dependencies
    - Identifying entry points and dead code
    - Impact analysis for changes
    - Detecting circular dependencies

    Args:
        parameters: Dictionary with:
            - programs: Dictionary of program information from analyze_program_system
            - call_graph: Raw call relationships
            - output_format: Graph format (dict, dot, json, mermaid) (default: dict)
            - include_metrics: Include graph metrics (default: True)

    Returns:
        Dictionary containing:
            - nodes: List of program nodes with attributes
            - edges: List of call edges with attributes
            - metrics: Graph-level metrics (cycles, depth, components)
            - visualization: Graph in requested format
    """
    try:
        programs = parameters.get("programs", {})
        call_graph = parameters.get("call_graph", {})
        output_format = parameters.get("output_format", "dict")
        include_metrics = parameters.get("include_metrics", True)

        if not programs and not call_graph:
            return {
                "success": False,
                "error": "Either programs or call_graph must be provided",
            }

        # Build nodes list
        nodes = []
        for program_id, info in programs.items():
            node = {
                "id": program_id,
                "label": program_id,
                "type": "program",
                "metrics": {
                    "fan_in": len(info.get("callers", [])),
                    "fan_out": len(info.get("callees", [])),
                    "size": info.get("size_metrics", {}).get("total_lines", 0),
                },
                "attributes": {
                    "file_path": info.get("file_path"),
                    "is_entry_point": len(info.get("callers", [])) == 0,
                    "is_leaf": len(info.get("callees", [])) == 0,
                },
            }
            nodes.append(node)

        # Build edges list
        edges = []
        edge_id = 0
        for caller, callees in call_graph.items():
            for callee in callees:
                edge = {
                    "id": edge_id,
                    "source": caller,
                    "target": callee,
                    "type": "calls",
                    "weight": 1,  # Could be enhanced with call frequency if available
                }
                edges.append(edge)
                edge_id += 1

        # Calculate metrics if requested
        metrics = {}
        if include_metrics:
            # Detect cycles using DFS
            def find_cycles() -> list[list[str]]:
                cycles: list[list[str]] = []
                visited: set[str] = set()
                rec_stack: set[str] = set()

                def dfs(node: str, path: list[str]) -> bool:
                    visited.add(node)
                    rec_stack.add(node)
                    path.append(node)

                    for neighbor in call_graph.get(node, []):
                        if neighbor not in visited:
                            if dfs(neighbor, path.copy()):
                                return True
                        elif neighbor in rec_stack:
                            # Found a cycle
                            cycle_start = path.index(neighbor)
                            cycles.append([*path[cycle_start:], neighbor])

                    rec_stack.remove(node)
                    return False

                for node in programs:
                    if node not in visited:
                        dfs(node, [])

                return cycles

            cycles = find_cycles()

            # Find strongly connected components
            def find_components() -> list[list[str]]:
                # Tarjan's algorithm for SCCs
                index_counter = [0]
                stack: list[str] = []
                lowlinks: dict[str, int] = {}
                index: dict[str, int] = {}
                on_stack: dict[str, bool] = {}
                components: list[list[str]] = []

                def strongconnect(v: str) -> None:
                    index[v] = index_counter[0]
                    lowlinks[v] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(v)
                    on_stack[v] = True

                    for w in call_graph.get(v, []):
                        if w not in index:
                            strongconnect(w)
                            lowlinks[v] = min(lowlinks[v], lowlinks[w])
                        elif on_stack.get(w, False):
                            lowlinks[v] = min(lowlinks[v], index[w])

                    if lowlinks[v] == index[v]:
                        component = []
                        while True:
                            w = stack.pop()
                            on_stack[w] = False
                            component.append(w)
                            if w == v:
                                break
                        components.append(component)

                for v in programs:
                    if v not in index:
                        strongconnect(v)

                return components

            components = find_components()

            metrics = {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "has_cycles": len(cycles) > 0,
                "cycle_count": len(cycles),
                "cycles": cycles,
                "strongly_connected_components": len(components),
                "largest_component_size": max(len(c) for c in components) if components else 0,
                "density": len(edges) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0,
            }

        # Generate visualization in requested format
        visualization = None
        if output_format == "dot":
            # Generate Graphviz DOT format
            dot_lines = ["digraph CallGraph {"]
            dot_lines.append("  rankdir=TB;")
            dot_lines.append("  node [shape=box];")

            for node in nodes:
                attrs = []
                if node["attributes"]["is_entry_point"]:
                    attrs.append("style=filled,fillcolor=lightgreen")
                elif node["attributes"]["is_leaf"]:
                    attrs.append("style=filled,fillcolor=lightblue")

                attr_str = f'[{",".join(attrs)}]' if attrs else ""
                dot_lines.append(f'  "{node["id"]}" {attr_str};')

            for edge in edges:
                dot_lines.append(f'  "{edge["source"]}" -> "{edge["target"]}";')

            dot_lines.append("}")
            visualization = "\n".join(dot_lines)

        elif output_format == "mermaid":
            # Generate Mermaid diagram format
            mermaid_lines = ["graph TD"]

            for node in nodes:
                shape = "([" if node["attributes"]["is_entry_point"] else "["
                shape_end = "])" if node["attributes"]["is_entry_point"] else "]"
                mermaid_lines.append(f'  {node["id"]}{shape}{node["label"]}{shape_end}')

            for edge in edges:
                mermaid_lines.append(f'  {edge["source"]} --> {edge["target"]}')

            visualization = "\n".join(mermaid_lines)

        return {
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "metrics": metrics,
            "visualization": visualization,
            "format": output_format,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to build call graph: {e!s}",
        }


def analyze_copybook_usage_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Analyze COPYBOOK usage patterns across COBOL programs.

    This tool identifies:
    - Which programs use which copybooks
    - Shared copybook dependencies
    - Copybook impact analysis (which programs affected by copybook changes)
    - Unused copybooks
    - Most frequently used copybooks

    Args:
        parameters: Dictionary with:
            - copybook_usage: Dictionary of copybook -> programs mapping
            - programs: Optional program information dictionary
            - include_recommendations: Generate optimization recommendations (default: True)

    Returns:
        Dictionary containing:
            - copybooks: List of copybook analysis records
            - usage_matrix: Programs vs copybooks matrix
            - impact_analysis: Programs affected by each copybook
            - recommendations: Suggested optimizations
    """
    try:
        copybook_usage = parameters.get("copybook_usage", {})
        programs = parameters.get("programs", {})
        include_recommendations = parameters.get("include_recommendations", True)

        if not copybook_usage:
            return {
                "success": True,
                "warning": "No copybook usage data provided",
                "copybooks": [],
                "usage_matrix": {},
                "impact_analysis": {},
                "recommendations": [],
            }

        # Analyze each copybook
        copybooks = []
        for copybook_name, using_programs in copybook_usage.items():
            copybook_info = {
                "name": copybook_name,
                "usage_count": len(using_programs),
                "used_by": list(using_programs),
                "usage_percentage": len(using_programs) / len(programs) * 100 if programs else 0,
                "is_shared": len(using_programs) > 1,
                "is_heavily_used": len(using_programs) > 5,  # Threshold can be adjusted
            }
            copybooks.append(copybook_info)

        # Sort by usage count
        copybooks.sort(key=lambda x: x["usage_count"], reverse=True)

        # Build usage matrix (programs vs copybooks)
        usage_matrix: dict[str, list[str]] = {}
        all_programs = set()

        for copybook_name, using_programs in copybook_usage.items():
            all_programs.update(using_programs)
            for program in using_programs:
                if program not in usage_matrix:
                    usage_matrix[program] = []
                usage_matrix[program].append(copybook_name)

        # Impact analysis - reverse mapping for change impact
        impact_analysis = {}
        for copybook in copybooks:
            impact_analysis[copybook["name"]] = {
                "directly_affected": copybook["used_by"],
                "affected_count": copybook["usage_count"],
                "risk_level": "HIGH"
                if copybook["usage_count"] > 10
                else "MEDIUM"
                if copybook["usage_count"] > 5
                else "LOW",
                "change_complexity": "Complex"
                if copybook["is_heavily_used"]
                else "Moderate"
                if copybook["is_shared"]
                else "Simple",
            }

        # Generate recommendations if requested
        recommendations = []
        if include_recommendations:
            # Find potential consolidation candidates
            single_use_copybooks = [c for c in copybooks if c["usage_count"] == 1]
            if single_use_copybooks:
                recommendations.append(
                    {
                        "type": "CONSOLIDATION",
                        "priority": "LOW",
                        "description": (
                            f"Consider consolidating {len(single_use_copybooks)} single-use copybooks"
                        ),
                        "copybooks": [c["name"] for c in single_use_copybooks[:5]],  # Show first 5
                    }
                )

            # Find heavily shared copybooks that might need refactoring
            heavily_shared = [c for c in copybooks if c["usage_count"] > 10]
            if heavily_shared:
                recommendations.append(
                    {
                        "type": "REFACTORING",
                        "priority": "MEDIUM",
                        "description": f"{len(heavily_shared)} copybooks are used by >10 programs",
                        "copybooks": [c["name"] for c in heavily_shared],
                        "suggestion": "Consider breaking down into smaller, more focused copybooks",
                    }
                )

            # Find programs with too many copybook dependencies
            heavy_users = [
                (prog, copies)
                for prog, copies in usage_matrix.items()
                if len(copies) > 15  # Threshold can be adjusted
            ]
            if heavy_users:
                recommendations.append(
                    {
                        "type": "DEPENDENCY_REDUCTION",
                        "priority": "HIGH",
                        "description": f"{len(heavy_users)} programs have >15 copybook dependencies",
                        "programs": [prog for prog, _ in heavy_users[:5]],  # Show first 5
                        "suggestion": "Review for potential consolidation or modularization",
                    }
                )

        # Calculate summary statistics
        stats = {
            "total_copybooks": len(copybooks),
            "total_relationships": sum(c["usage_count"] for c in copybooks),
            "average_usage": (
                sum(c["usage_count"] for c in copybooks) / len(copybooks) if copybooks else 0
            ),
            "max_usage": max((c["usage_count"] for c in copybooks), default=0),
            "single_use_count": len(single_use_copybooks) if include_recommendations else 0,
            "shared_count": len([c for c in copybooks if c["is_shared"]]),
        }

        return {
            "success": True,
            "copybooks": copybooks,
            "usage_matrix": usage_matrix,
            "impact_analysis": impact_analysis,
            "recommendations": recommendations,
            "statistics": stats,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to analyze copybook usage: {e!s}",
        }


def analyze_data_flow_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    """Analyze data flow through program parameters (BY VALUE/REFERENCE).

    This tool tracks how data flows between programs through CALL parameters,
    identifying:
    - Parameter passing patterns (BY VALUE vs BY REFERENCE)
    - Data dependencies between programs
    - Potential data integrity issues
    - Parameter type mismatches

    Args:
        parameters: Dictionary with:
            - data_flows: List of data flow records from analyze_program_system
            - programs: Optional program information
            - trace_variable: Optional specific variable to trace through the system

    Returns:
        Dictionary containing:
            - flows: Analyzed data flow records
            - chains: Data flow chains showing multi-hop flows
            - warnings: Potential issues detected
            - variable_usage: Usage patterns for traced variables
    """
    try:
        data_flows = parameters.get("data_flows", [])
        programs = parameters.get("programs", {})
        trace_variable = parameters.get("trace_variable")

        if not data_flows:
            return {
                "success": True,
                "warning": "No data flow information provided",
                "flows": [],
                "chains": [],
                "warnings": [],
                "variable_usage": {},
            }

        # Analyze each flow
        analyzed_flows = []
        parameter_types: dict[str, list[dict[str, Any]]] = {}  # Track parameter types across calls

        for flow in data_flows:
            analyzed = {
                "from": flow.get("from"),
                "to": flow.get("to"),
                "type": flow.get("type", "CALL"),
                "parameters": [],
            }

            # Analyze each parameter
            for param in flow.get("parameters", []):
                param_info = {
                    "name": param.get("name"),
                    "passing_mode": param.get("mode", "BY REFERENCE"),  # COBOL default
                    "data_type": param.get("type"),
                    "size": param.get("size"),
                    "is_modified": param.get("mode") == "BY REFERENCE",
                }
                analyzed["parameters"].append(param_info)

                # Track parameter types for mismatch detection
                param_key = f"{flow['to']}.{param.get('name')}"
                if param_key not in parameter_types:
                    parameter_types[param_key] = []
                parameter_types[param_key].append(
                    {
                        "caller": flow["from"],
                        "type": param.get("type"),
                        "size": param.get("size"),
                    }
                )

            analyzed_flows.append(analyzed)

        # Build data flow chains (trace multi-hop flows)
        chains = []
        if trace_variable:
            # Trace specific variable through the system
            def trace_flow(
                variable: str, start_program: str, visited: set[str] | None = None
            ) -> list[str]:
                if visited is None:
                    visited = set()

                if start_program in visited:
                    return []  # Avoid cycles

                visited.add(start_program)
                chain = [start_program]

                # Find outgoing flows from this program
                for flow in analyzed_flows:
                    if flow["from"] == start_program:
                        for param in flow["parameters"]:
                            if param["name"] == variable:
                                # Found flow of this variable
                                sub_chain = trace_flow(variable, flow["to"], visited.copy())
                                if sub_chain:
                                    return chain + sub_chain
                                else:
                                    return [*chain, flow["to"]]

                return chain

            # Trace from all entry points
            entry_points = [pid for pid, info in programs.items() if not info.get("callers")]

            for entry in entry_points:
                chain = trace_flow(trace_variable, entry)
                if len(chain) > 1:
                    chains.append(
                        {
                            "variable": trace_variable,
                            "start": entry,
                            "path": chain,
                            "length": len(chain),
                        }
                    )

        # Detect warnings and potential issues
        warnings: list[dict[str, Any]] = []

        # Check for parameter type mismatches
        for param_key, callers in parameter_types.items():
            if len(callers) > 1:
                types = {c["type"] for c in callers if c["type"]}
                sizes = {c["size"] for c in callers if c["size"]}

                if len(types) > 1 or len(sizes) > 1:
                    warnings.append(
                        {
                            "type": "PARAMETER_MISMATCH",
                            "severity": "HIGH",
                            "parameter": param_key,
                            "callers": [c["caller"] for c in callers],
                            "details": f"Inconsistent types: {types}, sizes: {sizes}",
                        }
                    )

        # Check for excessive parameter passing
        for flow in analyzed_flows:
            if len(flow["parameters"]) > 10:
                warnings.append(
                    {
                        "type": "EXCESSIVE_PARAMETERS",
                        "severity": "MEDIUM",
                        "from": flow["from"],
                        "to": flow["to"],
                        "parameter_count": len(flow["parameters"]),
                        "suggestion": "Consider using a data structure or reducing parameters",
                    }
                )

        # Analyze BY REFERENCE usage for potential side effects
        by_reference_flows = []
        for flow in analyzed_flows:
            ref_params = [p for p in flow["parameters"] if p["is_modified"]]
            if ref_params:
                by_reference_flows.append(
                    {
                        "from": flow["from"],
                        "to": flow["to"],
                        "modified_params": [p["name"] for p in ref_params],
                        "count": len(ref_params),
                    }
                )

                if len(ref_params) > 5:
                    warnings.append(
                        {
                            "type": "EXCESSIVE_SIDE_EFFECTS",
                            "severity": "MEDIUM",
                            "from": flow["from"],
                            "to": flow["to"],
                            "parameter_count": len(ref_params),
                            "suggestion": "Many BY REFERENCE parameters may cause side effects",
                        }
                    )

        # Build variable usage summary
        variable_usage: dict[str, dict[str, Any]] = {}
        for flow in analyzed_flows:
            for param in flow["parameters"]:
                var_name = param["name"]
                if var_name:
                    if var_name not in variable_usage:
                        variable_usage[var_name] = {
                            "occurrences": 0,
                            "programs": set(),
                            "by_value_count": 0,
                            "by_reference_count": 0,
                        }

                    var_info = variable_usage[var_name]
                    var_info["occurrences"] += 1
                    var_info["programs"].add(flow["from"])
                    var_info["programs"].add(flow["to"])

                    if param["passing_mode"] == "BY VALUE":
                        var_info["by_value_count"] += 1
                    else:
                        var_info["by_reference_count"] += 1

        # Convert sets to lists for JSON serialization
        for _var_name, var_info in variable_usage.items():
            var_info["programs"] = list(var_info["programs"])

        # Calculate statistics
        stats = {
            "total_flows": len(analyzed_flows),
            "total_parameters": sum(len(f["parameters"]) for f in analyzed_flows),
            "by_reference_flows": len(by_reference_flows),
            "unique_variables": len(variable_usage),
            "warnings_count": len(warnings),
        }

        return {
            "success": True,
            "flows": analyzed_flows,
            "chains": chains,
            "warnings": warnings,
            "variable_usage": variable_usage,
            "by_reference_summary": by_reference_flows,
            "statistics": stats,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to analyze data flow: {e!s}",
        }


def resolve_copybooks_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0915
    """Resolve COPY/COPYBOOK statements by replacing them with actual copybook content.

    This tool acts as a COBOL preprocessor that expands all COPY statements,
    generating a new "flattened" file with all copybooks inlined.

    Args:
        parameters: Dictionary with:
            - source_file: Path to COBOL source file with COPY statements
            - copybook_paths: List of directories to search for copybooks
            - output_file: Optional path to save resolved file
            - keep_markers: Add comment markers showing copybook boundaries (default: True)

    Returns:
        Dictionary containing:
            - success: Whether resolution succeeded
            - resolved_source: Complete source with COPY statements expanded
            - copybooks_resolved: List of copybooks that were resolved
            - copybooks_missing: List of copybooks that couldn't be found
            - output_file: Path to saved file (if requested)
            - line_mapping: Original line -> expanded line mapping
    """
    try:
        source_file = parameters.get("source_file")
        if not source_file:
            return {
                "success": False,
                "error": "source_file is required",
            }

        source_path = Path(source_file)
        if not source_path.exists():
            return {
                "success": False,
                "error": f"Source file not found: {source_file}",
            }

        copybook_paths = parameters.get("copybook_paths", [])
        output_file = parameters.get("output_file")
        keep_markers = parameters.get("keep_markers", True)

        # Convert copybook paths to Path objects
        search_dirs = [Path(p) for p in copybook_paths]

        # Read source file
        with source_path.open("r") as f:
            source_lines = f.readlines()

        resolved_lines: list[str] = []
        copybooks_resolved: list[dict[str, Any]] = []
        copybooks_missing: list[str] = []
        line_mapping: dict[int, int] = {}  # original_line -> expanded_line

        current_output_line = 1

        # Process each line
        for line_num, line in enumerate(source_lines, start=1):
            stripped = line.strip().upper()

            # Check if this is a COPY statement
            if stripped.startswith("COPY ") or "COPY " in stripped:
                # Extract copybook name from COPY statement
                # Format: COPY COPYBOOK-NAME.
                copybook_name = _extract_copybook_name(line)

                if copybook_name:
                    # Search for copybook file
                    copybook_file = _find_copybook_file(copybook_name, search_dirs)

                    if copybook_file:
                        # Read copybook content
                        with copybook_file.open("r") as f:
                            copybook_content = f.read()

                        # Add marker comment if requested
                        if keep_markers:
                            marker_start = (
                                f"      *> START COPYBOOK: {copybook_name} "
                                f"(from {copybook_file.name})\n"
                            )
                            resolved_lines.append(marker_start)
                            current_output_line += 1

                        # Add copybook content
                        copybook_lines = copybook_content.splitlines(keepends=True)
                        resolved_lines.extend(copybook_lines)
                        current_output_line += len(copybook_lines)

                        # Add marker comment if requested
                        if keep_markers:
                            marker_end = f"      *> END COPYBOOK: {copybook_name}\n"
                            resolved_lines.append(marker_end)
                            current_output_line += 1

                        copybooks_resolved.append(
                            {
                                "name": copybook_name,
                                "file": str(copybook_file),
                                "original_line": line_num,
                                "expanded_lines": len(copybook_lines),
                            }
                        )

                        logger.info(
                            f"Resolved COPYBOOK '{copybook_name}' from {copybook_file} "
                            f"({len(copybook_lines)} lines)"
                        )
                    else:
                        # Copybook not found - keep original COPY statement as comment
                        copybooks_missing.append(copybook_name)
                        warning_comment = f"      *> WARNING: COPYBOOK NOT FOUND: {copybook_name}\n"
                        resolved_lines.append(warning_comment)
                        resolved_lines.append(f"      *> {line}")
                        current_output_line += 2

                        logger.warning(
                            f"Copybook '{copybook_name}' not found in search paths: "
                            f"{[str(p) for p in search_dirs]}"
                        )

                    # Map original line to output line
                    line_mapping[line_num] = current_output_line
                else:
                    # Couldn't parse COPY statement - keep original
                    resolved_lines.append(line)
                    line_mapping[line_num] = current_output_line
                    current_output_line += 1
            else:
                # Regular line - keep as-is
                resolved_lines.append(line)
                line_mapping[line_num] = current_output_line
                current_output_line += 1

        # Join resolved lines
        resolved_source = "".join(resolved_lines)

        # Save to output file if requested
        saved_file = None
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(resolved_source)
            saved_file = str(output_path)
            logger.info(f"Saved resolved COBOL to {saved_file}")

        return {
            "success": True,
            "resolved_source": resolved_source,
            "copybooks_resolved": copybooks_resolved,
            "copybooks_missing": copybooks_missing,
            "total_copybooks": len(copybooks_resolved),
            "missing_count": len(copybooks_missing),
            "output_file": saved_file,
            "line_mapping": line_mapping,
            "original_lines": len(source_lines),
            "expanded_lines": len(resolved_lines),
        }

    except Exception as e:
        logger.exception("Failed to resolve copybooks")
        return {
            "success": False,
            "error": f"Failed to resolve copybooks: {e!s}",
        }


def _extract_copybook_name(copy_line: str) -> str | None:
    """Extract copybook name from a COPY statement.

    Handles formats like:
    - COPY COPYBOOK-NAME.
    - COPY "COPYBOOK-NAME".
    - COPY 'COPYBOOK-NAME'.

    Args:
        copy_line: Line containing COPY statement

    Returns:
        Copybook name or None if not found
    """
    # Remove leading spaces and comments
    line = copy_line.strip()
    if line.startswith("*"):
        return None

    # Match COPY statement
    # Pattern: COPY followed by name (with optional quotes) and optional period
    pattern = r"COPY\s+['\"]?([A-Za-z0-9\-_]+)['\"]?\s*\.?"
    match = re.search(pattern, line, re.IGNORECASE)

    if match:
        return match.group(1)

    return None


def prepare_cobol_for_antlr_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Prepare COBOL source for ANTLR parser by removing unsupported optional paragraphs.

    The ANTLR Cobol85.g4 grammar doesn't support optional IDENTIFICATION DIVISION
    paragraphs like AUTHOR, DATE-WRITTEN, etc. This tool removes them to make
    files compatible with the parser.

    Args:
        parameters: Dictionary with:
            - source_code: COBOL source code as string (optional)
            - source_file: Path to COBOL source file (optional)
            - output_file: Path to save cleaned file (optional)

    Returns:
        Dictionary containing:
            - success: Whether cleaning succeeded
            - cleaned_source: COBOL source with optional paragraphs removed
            - paragraphs_removed: List of paragraph types that were removed
            - output_file: Path to saved file (if requested)
    """
    try:
        source_code = parameters.get("source_code")
        source_file = parameters.get("source_file")
        output_file = parameters.get("output_file")

        if not source_code and not source_file:
            return {
                "success": False,
                "error": "Either 'source_code' or 'source_file' must be provided",
            }

        # Read source file if provided
        if source_file:
            source_path = Path(source_file)
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source file not found: {source_file}",
                }
            with source_path.open("r") as f:
                source_code = f.read()

        # Ensure source_code is not None (mypy type check)
        if source_code is None:
            return {
                "success": False,
                "error": "source_code is None after reading file",
            }

        # Remove optional paragraphs
        cleaned_source, removed_paragraphs = _remove_optional_paragraphs(source_code)

        # Save to output file if requested
        saved_file = None
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(cleaned_source)
            saved_file = str(output_path)
            logger.info(f"Saved cleaned COBOL to {saved_file}")

        return {
            "success": True,
            "cleaned_source": cleaned_source,
            "paragraphs_removed": removed_paragraphs,
            "output_file": saved_file,
        }

    except Exception as e:
        logger.exception("Failed to prepare COBOL for ANTLR")
        return {
            "success": False,
            "error": f"Failed to prepare COBOL: {e!s}",
        }


def _remove_optional_paragraphs(cobol_source: str) -> tuple[str, list[str]]:
    """Remove optional identification division paragraphs.

    Removes:
    - AUTHOR paragraph
    - DATE-WRITTEN paragraph
    - DATE-COMPILED paragraph
    - INSTALLATION paragraph
    - SECURITY paragraph
    - REMARKS paragraph

    Args:
        cobol_source: Original COBOL source code

    Returns:
        Tuple of (cleaned source code, list of removed paragraph types)
    """
    lines = cobol_source.split("\n")
    cleaned_lines = []
    skip_line = False
    removed_paragraphs: list[str] = []

    optional_keywords = [
        "AUTHOR.",
        "DATE-WRITTEN.",
        "DATE-COMPILED.",
        "INSTALLATION.",
        "SECURITY.",
        "REMARKS.",
    ]

    for line in lines:
        # Check if this is an optional paragraph header
        upper_line = line.upper().strip()

        # Check if we found an optional paragraph
        for keyword in optional_keywords:
            if keyword in upper_line:
                skip_line = True
                # Extract paragraph name (e.g., "AUTHOR" from "AUTHOR.")
                para_name = keyword.rstrip(".")
                if para_name not in removed_paragraphs:
                    removed_paragraphs.append(para_name)
                break

        # Check if we've reached the next division or another paragraph
        if any(
            keyword in upper_line
            for keyword in [
                "DATA DIVISION",
                "ENVIRONMENT DIVISION",
                "PROCEDURE DIVISION",
                "PROGRAM-ID.",
            ]
        ):
            skip_line = False

        if not skip_line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines), removed_paragraphs


def batch_resolve_copybooks_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Batch resolve COPY statements for all COBOL files in a directory.

    This tool:
    1. Finds all COBOL files with COPY statements
    2. Resolves copybooks by inserting actual content
    3. Renames originals to .original extension
    4. Saves resolved files with the original name

    Args:
        parameters: Dictionary with:
            - directory: Directory containing COBOL files
            - copybook_paths: List of directories to search for copybooks
            - file_extensions: List of extensions to process (default: ['.cbl', '.cob', '.cobol'])
            - recursive: Search subdirectories (default: False)
            - keep_markers: Add copybook boundary markers (default: True)
            - backup_originals: Rename originals to .original (default: True)

    Returns:
        Dictionary containing:
            - success: Whether batch processing succeeded
            - files_processed: List of successfully processed files
            - files_failed: List of files that failed
            - total_files: Total files found
            - total_copybooks_resolved: Total copybooks expanded
            - summary: Processing summary
    """
    try:
        directory = parameters.get("directory")
        if not directory:
            return {
                "success": False,
                "error": "directory is required",
            }

        dir_path = Path(directory)
        if not dir_path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {directory}",
            }

        copybook_paths = parameters.get("copybook_paths", [])
        file_extensions = parameters.get("file_extensions", [".cbl", ".cob", ".cobol"])
        recursive = parameters.get("recursive", False)
        keep_markers = parameters.get("keep_markers", True)
        backup_originals = parameters.get("backup_originals", True)

        # Find all COBOL files
        cobol_files: list[Path] = []
        if recursive:
            for ext in file_extensions:
                cobol_files.extend(dir_path.rglob(f"*{ext}"))
        else:
            for ext in file_extensions:
                cobol_files.extend(dir_path.glob(f"*{ext}"))

        # Filter out .original files
        cobol_files = [f for f in cobol_files if not f.name.endswith(".original")]

        if not cobol_files:
            return {
                "success": True,
                "warning": f"No COBOL files found in {directory}",
                "files_processed": [],
                "files_failed": [],
                "total_files": 0,
            }

        files_processed: list[dict[str, Any]] = []
        files_failed: list[dict[str, Any]] = []
        total_copybooks_resolved = 0

        logger.info(f"Found {len(cobol_files)} COBOL files to process")

        for cobol_file in cobol_files:
            try:
                # Check if file has COPY statements
                with cobol_file.open("r") as f:
                    content = f.read()
                    has_copy = "COPY " in content.upper()

                if not has_copy:
                    logger.info(f"Skipping {cobol_file.name} - no COPY statements")
                    continue

                logger.info(f"Processing {cobol_file.name}...")

                # Resolve copybooks
                result = resolve_copybooks_handler(
                    {
                        "source_file": str(cobol_file),
                        "copybook_paths": copybook_paths,
                        "output_file": None,  # We'll handle output ourselves
                        "keep_markers": keep_markers,
                    }
                )

                if not result.get("success"):
                    files_failed.append(
                        {
                            "file": str(cobol_file),
                            "error": result.get("error"),
                        }
                    )
                    continue

                # Backup original file if requested
                if backup_originals:
                    original_backup = cobol_file.with_suffix(cobol_file.suffix + ".original")
                    cobol_file.rename(original_backup)
                    logger.info(f"Backed up original to {original_backup.name}")

                # Write resolved content to original filename
                with cobol_file.open("w") as f:
                    f.write(result["resolved_source"])

                files_processed.append(
                    {
                        "file": str(cobol_file),
                        "original_backup": str(original_backup) if backup_originals else None,
                        "original_lines": result["original_lines"],
                        "expanded_lines": result["expanded_lines"],
                        "copybooks_resolved": result["total_copybooks"],
                        "copybooks_missing": result["missing_count"],
                        "copybook_details": result["copybooks_resolved"],
                    }
                )

                total_copybooks_resolved += result["total_copybooks"]

                logger.info(
                    f"✓ Processed {cobol_file.name}: "
                    f"{result['original_lines']} → {result['expanded_lines']} lines, "
                    f"{result['total_copybooks']} copybooks resolved"
                )

            except Exception as e:
                logger.exception(f"Failed to process {cobol_file}")
                files_failed.append(
                    {
                        "file": str(cobol_file),
                        "error": str(e),
                    }
                )

        summary = {
            "total_files_found": len(cobol_files),
            "files_with_copy_statements": len(files_processed) + len(files_failed),
            "files_processed": len(files_processed),
            "files_failed": len(files_failed),
            "total_copybooks_resolved": total_copybooks_resolved,
        }

        return {
            "success": True,
            "files_processed": files_processed,
            "files_failed": files_failed,
            "summary": summary,
        }

    except Exception as e:
        logger.exception("Batch copybook resolution failed")
        return {
            "success": False,
            "error": f"Batch processing failed: {e!s}",
        }


def _find_copybook_file(copybook_name: str, search_dirs: list[Path]) -> Path | None:
    """Find copybook file in search directories.

    Searches for files with common copybook extensions: .cpy, .CPY, .cbl, .CBL, .copy, .COPY

    Args:
        copybook_name: Name of copybook to find
        search_dirs: List of directories to search

    Returns:
        Path to copybook file or None if not found
    """
    # Common copybook extensions
    extensions = [".cpy", ".CPY", ".cbl", ".CBL", ".copy", ".COPY", ""]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for ext in extensions:
            # Try exact name with extension
            copybook_file = search_dir / f"{copybook_name}{ext}"
            if copybook_file.exists() and copybook_file.is_file():
                return copybook_file

            # Try lowercase name with extension
            copybook_file = search_dir / f"{copybook_name.lower()}{ext}"
            if copybook_file.exists() and copybook_file.is_file():
                return copybook_file

            # Try uppercase name with extension
            copybook_file = search_dir / f"{copybook_name.upper()}{ext}"
            if copybook_file.exists() and copybook_file.is_file():
                return copybook_file

    return None


# ============================================================================
# Complexity Analysis and Graph Building Handlers
# ============================================================================


def analyze_complexity_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    """Analyze complexity of COBOL source code.

    This handler computes complexity metrics from the AST including:
    - Line metrics (LOC, comments, blank lines)
    - Structural metrics (divisions, sections, paragraphs, statements)
    - Control flow metrics (IF, EVALUATE, PERFORM, GO TO counts)
    - Data metrics (data items, levels, REDEFINES)
    - Overall complexity rating (LOW, MEDIUM, HIGH, VERY_HIGH)

    Optionally builds ASG, CFG, and/or DFG to enhance metrics with:
    - Symbol tables and cross-references (from ASG)
    - Accurate cyclomatic complexity (from CFG)
    - Unreachable code detection (from CFG)
    - Dead variable detection (from DFG)
    - Uninitialized read detection (from DFG)

    Args:
        parameters: Handler parameters containing:
            - 'source_code': COBOL source code string
            - 'file_path': Path to COBOL file
            - 'ast': Pre-built AST (dict or ParseNode) to avoid re-parsing
            - 'include_recommendations': Generate analysis recommendations (default: True)
            - 'build_asg': Build ASG for semantic analysis and cross-references (default: False)
            - 'build_cfg': Build CFG for accurate cyclomatic complexity (default: False)
            - 'build_dfg': Build DFG for dead/uninitialized variable detection (default: False)
            - 'auto_enhance': Auto-build ASG/CFG/DFG based on complexity (default: False)

    Returns:
        Dictionary with complexity metrics and rating
    """
    source_code = parameters.get("source_code")
    file_path = parameters.get("file_path")
    ast_input = parameters.get("ast")
    include_recommendations = parameters.get("include_recommendations", True)
    should_build_asg = parameters.get("build_asg", False)
    should_build_cfg = parameters.get("build_cfg", False)
    should_build_dfg = parameters.get("build_dfg", False)
    auto_enhance = parameters.get("auto_enhance", False)

    if not source_code and not file_path and not ast_input:
        return {
            "success": False,
            "error": "Either 'source_code', 'file_path', or 'ast' must be provided",
        }

    try:
        # Get or build AST
        if ast_input:
            ast = _deserialize_parse_node(ast_input) if isinstance(ast_input, dict) else ast_input
            source_lines: list[str] = []
        # Parse source to get AST
        elif file_path:
            ast, _comments, _ = parse_cobol_file(file_path)
            with Path(file_path).open() as f:
                source_lines = f.readlines()
        else:
            assert source_code is not None  # nosec B101
            ast, _comments, _ = parse_cobol(source_code)
            source_lines = source_code.splitlines()

        # Initialize complexity metrics
        metrics = ComplexityMetrics(
            program_name=_extract_program_name_from_parse_tree(ast),
            source_file=file_path,
            analysis_level=AnalysisLevel.AST,
        )

        # Compute line metrics from source
        if source_lines:
            metrics.line_metrics = _compute_line_metrics(source_lines)

        # Compute structural metrics from AST
        metrics.structural_metrics = _compute_structural_metrics(ast)

        # Compute control flow metrics from AST
        metrics.control_flow_metrics = _compute_control_flow_metrics(ast)

        # Compute data metrics from AST
        metrics.data_metrics = _compute_data_metrics(ast)

        # Compute dependency metrics from AST
        metrics.dependency_metrics = _compute_dependency_metrics(ast)

        # Compute initial rating (before CFG/DFG enhancement)
        metrics.compute_complexity_rating()

        # Auto-enhance based on complexity:
        # - MEDIUM+: Build ASG for semantic analysis
        # - HIGH+: Also build CFG/DFG for control/data flow analysis
        if auto_enhance:
            if metrics.complexity_rating.value in ("MEDIUM", "HIGH", "VERY_HIGH"):
                should_build_asg = True
            if metrics.complexity_rating.value in ("HIGH", "VERY_HIGH"):
                should_build_cfg = True
                should_build_dfg = True

        # Build ASG if requested (provides semantic analysis, symbol tables, cross-references)
        if should_build_asg:
            try:
                if file_path:
                    asg_program = build_asg_from_file(file_path)
                elif source_code:
                    asg_program = build_asg_from_source(source_code)
                else:
                    # If only AST provided, we can't build ASG (need source)
                    logger.warning("Cannot build ASG without source_code or file_path")
                    asg_program = None

                if asg_program:
                    metrics.asg_metrics = _compute_asg_metrics(asg_program)
                    metrics.analysis_level = AnalysisLevel.ASG
                    logger.info(
                        f"Enhanced with ASG: {metrics.asg_metrics.symbol_count} symbols, "
                        f"{metrics.asg_metrics.resolved_references} resolved refs"
                    )
            except ASGBuilderError as e:
                logger.warning(f"ASG build failed during complexity analysis: {e}")

        # Serialize AST for CFG/DFG builders
        ast_dict = _serialize_parse_node(ast) if should_build_cfg or should_build_dfg else None

        # Build CFG if requested
        if should_build_cfg and ast_dict:
            try:
                cfg = build_cfg_from_ast(ast_dict, metrics.program_name)
                metrics.cfg_metrics = CFGMetrics(
                    node_count=cfg.node_count,
                    edge_count=cfg.edge_count,
                    unreachable_paragraphs=cfg.unreachable_nodes,
                    entry_points=[cfg.entry_node] if cfg.entry_node else [],
                    exit_points=cfg.exit_nodes,
                )
                # Update with accurate cyclomatic complexity
                metrics.control_flow_metrics.cyclomatic_complexity_accurate = (
                    cfg.cyclomatic_complexity
                )
                metrics.analysis_level = AnalysisLevel.CFG
                logger.info(f"Enhanced with CFG: CC={cfg.cyclomatic_complexity}")
            except CFGBuilderError as e:
                logger.warning(f"CFG build failed during complexity analysis: {e}")

        # Build DFG if requested
        if should_build_dfg and ast_dict:
            try:
                dfg = build_dfg_from_ast(ast_dict, metrics.program_name)
                metrics.dfg_metrics = DFGMetrics(
                    node_count=dfg.node_count,
                    edge_count=dfg.edge_count,
                    dead_variables=dfg.dead_variables,
                    uninitialized_reads=dfg.uninitialized_reads,
                    data_dependencies=dfg.data_dependencies,
                )
                metrics.analysis_level = AnalysisLevel.DFG
                logger.info(
                    f"Enhanced with DFG: {len(dfg.dead_variables)} dead vars, "
                    f"{len(dfg.uninitialized_reads)} uninitialized reads"
                )
            except DFGBuilderError as e:
                logger.warning(f"DFG build failed during complexity analysis: {e}")

        # Re-compute rating with enhanced metrics
        if should_build_asg or should_build_cfg or should_build_dfg:
            metrics.compute_complexity_rating()

        # Build result
        result: dict[str, Any] = {
            "success": True,
            "program_name": metrics.program_name,
            "complexity_rating": metrics.complexity_rating.value,
            "complexity_score": metrics.complexity_score,
            "analysis_level": metrics.analysis_level.value,
            "metrics": metrics.model_dump(mode="json", exclude_none=True),
        }

        # Add ASG-specific results if built
        if metrics.asg_metrics:
            result["symbol_count"] = metrics.asg_metrics.symbol_count
            result["resolved_references"] = metrics.asg_metrics.resolved_references
            result["unresolved_references"] = metrics.asg_metrics.unresolved_references
            result["external_calls"] = metrics.asg_metrics.external_calls

        # Add CFG-specific results if built
        if metrics.cfg_metrics:
            result[
                "cyclomatic_complexity_accurate"
            ] = metrics.control_flow_metrics.cyclomatic_complexity_accurate
            result["unreachable_code"] = metrics.cfg_metrics.unreachable_paragraphs

        # Add DFG-specific results if built
        if metrics.dfg_metrics:
            result["dead_variables"] = metrics.dfg_metrics.dead_variables
            result["uninitialized_reads"] = metrics.dfg_metrics.uninitialized_reads

        if include_recommendations:
            result["recommended_analysis"] = metrics.recommended_analysis
            result["warnings"] = metrics.quality_indicators.warnings
            result["recommendations"] = metrics.quality_indicators.recommendations

        # Save result
        saved_path = _save_tool_result(
            "analyze_complexity", result, metrics.program_name or "unknown"
        )
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result

    except Exception as e:
        logger.exception("Failed to analyze complexity")
        return {"success": False, "error": str(e)}


def _compute_line_metrics(source_lines: list[str]) -> LineMetrics:
    """Compute line-based metrics from source code."""
    total = len(source_lines)
    code = 0
    comments = 0
    blank = 0

    for line in source_lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
        elif stripped.startswith("*") or stripped.startswith("*>"):
            comments += 1
        elif len(line) >= 7 and line[6] == "*":
            # Column 7 asterisk is a comment in fixed format
            comments += 1
        else:
            code += 1

    return LineMetrics(
        total_lines=total,
        code_lines=code,
        comment_lines=comments,
        blank_lines=blank,
        comment_ratio=comments / code if code > 0 else 0.0,
    )


def _compute_structural_metrics(ast: ParseNode) -> StructuralMetrics:
    """Compute structural metrics from AST."""
    metrics = StructuralMetrics()

    # Count divisions
    divisions = _find_all_nodes(
        ast, ["IdentificationDivision", "EnvironmentDivision", "DataDivision", "ProcedureDivision"]
    )
    metrics.division_count = len(divisions)

    # Count sections
    sections = _find_all_nodes(ast, ["Section", "section", "procedureSection"])
    metrics.section_count = len(sections)

    # Count paragraphs
    paragraphs = _find_all_nodes(ast, ["Paragraph", "paragraph"])
    metrics.paragraph_count = len(paragraphs)

    # Count statements
    statements = _find_all_nodes(ast, ["Statement", "statement"])
    metrics.statement_count = len(statements)

    # Count data items
    data_entries = _find_all_nodes(
        ast, ["DataDescriptionEntry", "dataDescriptionEntry", "dataDescriptionEntryFormat1"]
    )
    metrics.data_item_count = len(data_entries)

    # Count level 88 conditions
    level_88 = _find_all_nodes(ast, ["DataDescriptionEntryFormat2", "conditionNameEntry"])
    metrics.level_88_count = len(level_88)

    # Count copybooks
    copy_stmts = _find_all_nodes(ast, ["CopyStatement", "copyStatement"])
    metrics.copybook_count = len(copy_stmts)

    return metrics


def _compute_control_flow_metrics(ast: ParseNode) -> ControlFlowMetrics:
    """Compute control flow metrics from AST."""
    metrics = ControlFlowMetrics()

    # Count IF statements
    if_stmts = _find_all_nodes(ast, ["IfStatement", "ifStatement"])
    metrics.if_count = len(if_stmts)

    # Count EVALUATE statements
    eval_stmts = _find_all_nodes(ast, ["EvaluateStatement", "evaluateStatement"])
    metrics.evaluate_count = len(eval_stmts)

    # Count PERFORM statements
    perform_stmts = _find_all_nodes(ast, ["PerformStatement", "performStatement"])
    metrics.perform_count = len(perform_stmts)

    # Count GO TO statements (bad practice)
    goto_stmts = _find_all_nodes(ast, ["GoToStatement", "gotoStatement", "goToStatement"])
    metrics.goto_count = len(goto_stmts)

    # Count ALTER statements (very bad practice)
    alter_stmts = _find_all_nodes(ast, ["AlterStatement", "alterStatement"])
    metrics.alter_count = len(alter_stmts)

    # Count CALL statements
    call_stmts = _find_all_nodes(ast, ["CallStatement", "callStatement"])
    metrics.call_count = len(call_stmts)

    # Approximate cyclomatic complexity from decision points
    # CC = 1 + IF + EVALUATE*when_count + PERFORM_UNTIL
    when_clauses = _find_all_nodes(ast, ["WhenPhrase", "whenPhrase"])
    metrics.cyclomatic_complexity = (
        1 + metrics.if_count + len(when_clauses) + metrics.evaluate_count
    )

    # Calculate max nesting depth
    metrics.max_nesting_depth = _calculate_max_nesting(ast)

    return metrics


def _calculate_max_nesting(node: ParseNode, current_depth: int = 0) -> int:
    """Calculate maximum nesting depth of control structures."""
    max_depth = current_depth

    # Check if this is a nesting construct
    if node.type and any(keyword in node.type.upper() for keyword in ["IF", "EVALUATE", "PERFORM"]):
        current_depth += 1
        max_depth = current_depth

    # Recurse into children
    for child in node.children:
        child_depth = _calculate_max_nesting(child, current_depth)
        max_depth = max(max_depth, child_depth)

    return max_depth


def _compute_data_metrics(ast: ParseNode) -> DataMetrics:
    """Compute data-related metrics from AST."""
    metrics = DataMetrics()

    # Find DATA DIVISION
    data_div = _find_node(ast, ["DataDivision", "dataDivision"])
    if not data_div:
        return metrics

    # Count WORKING-STORAGE items
    ws_section = _find_node(data_div, ["WorkingStorageSection", "workingStorageSection"])
    if ws_section:
        ws_entries = _find_all_nodes(ws_section, ["DataDescriptionEntry", "dataDescriptionEntry"])
        metrics.working_storage_items = len(ws_entries)

    # Count LINKAGE items
    linkage = _find_node(data_div, ["LinkageSection", "linkageSection"])
    if linkage:
        link_entries = _find_all_nodes(linkage, ["DataDescriptionEntry", "dataDescriptionEntry"])
        metrics.linkage_items = len(link_entries)

    # Count FILE SECTION items
    file_section = _find_node(data_div, ["FileSection", "fileSection"])
    if file_section:
        file_entries = _find_all_nodes(
            file_section, ["DataDescriptionEntry", "dataDescriptionEntry"]
        )
        metrics.file_section_items = len(file_entries)

    # Count REDEFINES
    redefines = _find_all_nodes(data_div, ["RedefinesClause", "redefinesClause"])
    metrics.redefines_count = len(redefines)

    # Count OCCURS
    occurs = _find_all_nodes(data_div, ["OccursClause", "occursClause"])
    metrics.occurs_count = len(occurs)

    # Count PICTURE clauses
    pictures = _find_all_nodes(data_div, ["PictureClause", "pictureClause"])
    metrics.picture_clauses = len(pictures)

    return metrics


def _compute_dependency_metrics(ast: ParseNode) -> DependencyMetrics:
    """Compute dependency metrics from AST."""
    metrics = DependencyMetrics()

    # Extract external calls
    call_stmts = _find_all_nodes(ast, ["CallStatement", "callStatement"])
    for call in call_stmts:
        target = _extract_call_target_from_node(call)
        if target and target not in metrics.external_calls:
            metrics.external_calls.append(target)

    metrics.fan_out = len(metrics.external_calls)

    # Extract copybooks
    copy_stmts = _find_all_nodes(ast, ["CopyStatement", "copyStatement"])
    for copy in copy_stmts:
        copybook = _extract_copybook_name_from_node(copy)
        if copybook and copybook not in metrics.copybooks_used:
            metrics.copybooks_used.append(copybook)

    return metrics


def _extract_call_target_from_node(node: ParseNode) -> str | None:
    """Extract call target from a CALL statement node."""
    for child in node.children:
        if child.type and "Literal" in child.type and child.text:
            return child.text.strip("'\"")
        if child.type and "Identifier" in child.type:
            if child.value:
                return str(child.value)
            if child.text:
                return child.text
    return None


def _extract_copybook_name_from_node(node: ParseNode) -> str | None:
    """Extract copybook name from a COPY statement node."""
    for child in node.children:
        if child.type and ("copySource" in child.type or "cobolWord" in child.type):
            if child.text:
                return child.text
            for sub in child.children:
                if sub.text:
                    return sub.text
    return None


def _find_node(node: ParseNode, type_names: list[str]) -> ParseNode | None:
    """Find a node by type name."""
    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        return node
    for child in node.children:
        result = _find_node(child, type_names)
        if result:
            return result
    return None


def _find_all_nodes(node: ParseNode, type_names: list[str]) -> list[ParseNode]:
    """Find all nodes matching type names."""
    results: list[ParseNode] = []
    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        results.append(node)
    for child in node.children:
        results.extend(_find_all_nodes(child, type_names))
    return results


def _compute_asg_metrics(program: Program) -> ASGMetrics:  # noqa: PLR0912
    """Compute ASG metrics from a Program object.

    Extracts semantic analysis metrics including:
    - Symbol counts (data items, paragraphs, sections)
    - Reference resolution statistics
    - External calls and internal procedure calls
    - Copybook usage
    """
    metrics = ASGMetrics()

    # Get first compilation unit (usually only one per file)
    if not program.compilation_units:
        return metrics

    comp_unit = program.compilation_units[0]
    if not comp_unit.program_units:
        return metrics

    program_unit = comp_unit.program_units[0]

    # Count symbols using SymbolTable
    try:
        symbol_table = SymbolTable.from_program_unit(program_unit)
        metrics.symbol_count = len(symbol_table.symbols)

        # Count by type
        for symbol in symbol_table.symbols.values():
            if symbol.symbol_type.value == "DATA_ITEM":
                metrics.data_item_count += 1
            elif symbol.symbol_type.value == "PARAGRAPH":
                metrics.paragraph_count += 1
            elif symbol.symbol_type.value == "SECTION":
                metrics.section_count += 1

        # Resolve references and count
        resolver = ReferenceResolver.from_program_unit(program_unit, symbol_table)

        # Count resolved vs unresolved
        for ref in resolver.resolved_references:
            if ref.status == ResolutionStatus.RESOLVED:
                metrics.resolved_references += 1
            elif ref.status == ResolutionStatus.NOT_FOUND:
                metrics.unresolved_references += 1
            elif (
                ref.status == ResolutionStatus.AMBIGUOUS
                and ref.name not in metrics.ambiguous_references
            ):
                metrics.ambiguous_references.append(ref.name)

        # External calls
        metrics.external_calls = list(resolver.external_calls.keys())

        # Internal calls (PERFORM targets)
        for ref in resolver.resolved_references:
            if (
                ref.reference_type.value == "PARAGRAPH"
                and ref.status == ResolutionStatus.RESOLVED
                and ref.resolved_symbol
                and ref.resolved_symbol not in metrics.internal_calls
            ):
                metrics.internal_calls.append(ref.resolved_symbol)

    except Exception as e:
        logger.warning(f"Error computing ASG metrics from symbol table: {e}")

    # Copybooks from program
    metrics.copybooks_used = list(program.external_copybooks)

    # Files from data division
    if program_unit.data_division and program_unit.data_division.file_section:
        for fd in program_unit.data_division.file_section.file_descriptions:
            if fd.name:
                metrics.files_defined.append(fd.name)

    # Entry points
    if program_unit.identification_division:
        entry_name = program_unit.identification_division.program_name
        if entry_name:
            metrics.entry_points.append(entry_name)

    return metrics


def build_cfg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build Control Flow Graph (CFG) from COBOL AST.

    The CFG represents all possible execution paths through the program.
    It requires an AST as input (from build_ast tool) to avoid re-parsing.

    This enables:
    - Accurate cyclomatic complexity calculation
    - Unreachable code detection
    - Control flow analysis for migration planning

    Args:
        parameters: Handler parameters containing:
            - 'ast': AST from build_ast tool (required)
            - 'program_name': Optional program name

    Returns:
        Dictionary with CFG structure and metrics
    """
    ast_input = parameters.get("ast")
    program_name = parameters.get("program_name")

    if not ast_input:
        return {
            "success": False,
            "error": "'ast' parameter is required. Use build_ast first to get the AST.",
        }

    try:
        # Build CFG from AST
        cfg: ControlFlowGraph = build_cfg_from_ast(ast_input, program_name)

        # Serialize CFG
        cfg_dict = serialize_cfg(cfg)

        result: dict[str, Any] = {
            "success": True,
            "cfg": cfg_dict,
            "program_name": cfg.program_name,
            "cyclomatic_complexity": cfg.cyclomatic_complexity,
            "node_count": cfg.node_count,
            "edge_count": cfg.edge_count,
            "unreachable_nodes": cfg.unreachable_nodes,
            "entry_node": cfg.entry_node,
            "exit_nodes": cfg.exit_nodes,
        }

        # Save result
        saved_path = _save_tool_result("build_cfg", result, program_name or "unknown")
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result

    except CFGBuilderError as e:
        logger.warning(f"CFG build failed: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("Failed to build CFG")
        return {"success": False, "error": str(e)}


def build_dfg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build Data Flow Graph (DFG) from COBOL AST.

    The DFG tracks how data flows through the program.
    It requires an AST as input (from build_ast tool) to avoid re-parsing.

    This enables:
    - Dead variable detection (assigned but never read)
    - Uninitialized variable detection (read before assignment)
    - Data dependency analysis for refactoring

    Args:
        parameters: Handler parameters containing:
            - 'ast': AST from build_ast tool (required)
            - 'program_name': Optional program name

    Returns:
        Dictionary with DFG structure and analysis results
    """
    ast_input = parameters.get("ast")
    program_name = parameters.get("program_name")

    if not ast_input:
        return {
            "success": False,
            "error": "'ast' parameter is required. Use build_ast first to get the AST.",
        }

    try:
        # Build DFG from AST
        dfg: DataFlowGraph = build_dfg_from_ast(ast_input, program_name)

        # Serialize DFG
        dfg_dict = serialize_dfg(dfg)

        result: dict[str, Any] = {
            "success": True,
            "dfg": dfg_dict,
            "program_name": dfg.program_name,
            "node_count": dfg.node_count,
            "edge_count": dfg.edge_count,
            "dead_variables": dfg.dead_variables,
            "uninitialized_reads": dfg.uninitialized_reads,
            "data_dependencies": dfg.data_dependencies,
            "variable_count": len(dfg.variables),
        }

        # Save result
        saved_path = _save_tool_result("build_dfg", result, program_name or "unknown")
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result

    except DFGBuilderError as e:
        logger.warning(f"DFG build failed: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("Failed to build DFG")
        return {"success": False, "error": str(e)}


# Registry mapping handler names to handler functions
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "parse_cobol_handler": parse_cobol_handler,
    "parse_cobol_raw_handler": parse_cobol_raw_handler,
    "build_ast_handler": build_ast_handler,
    "build_asg_handler": build_asg_handler,
    "analyze_complexity_handler": analyze_complexity_handler,
    "build_cfg_handler": build_cfg_handler,
    "build_dfg_handler": build_dfg_handler,
    "batch_analyze_cobol_directory_handler": batch_analyze_cobol_directory_handler,
    "analyze_program_system_handler": analyze_program_system_handler,
    "build_call_graph_handler": build_call_graph_handler,
    "analyze_copybook_usage_handler": analyze_copybook_usage_handler,
    "analyze_data_flow_handler": analyze_data_flow_handler,
    "prepare_cobol_for_antlr_handler": prepare_cobol_for_antlr_handler,
    "resolve_copybooks_handler": resolve_copybooks_handler,
    "batch_resolve_copybooks_handler": batch_resolve_copybooks_handler,
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

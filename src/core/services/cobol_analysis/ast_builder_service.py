"""AST Builder Service for COBOL analysis.

This module provides Abstract Syntax Tree (AST) building functionality for COBOL
source code. It encapsulates all AST-related operations including:
- Parsing COBOL source to AST (ParseNode)
- Serialization/deserialization of ParseNode structures
- Program name and metadata extraction
- Copybook resolution
- Node traversal utilities

The AST (ParseNode) serves as the foundation for further analysis:
- ASG (Abstract Semantic Graph) building
- CFG (Control Flow Graph) building
- DFG (Data Flow Graph) building
- Call graph generation
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.services.cobol_analysis.cobol_parser_antlr_service import (
    Comment,
    IdentificationMetadata,
    ParseNode,
    parse_cobol,
    parse_cobol_file,
    parse_cobol_file_with_copybooks,
    parse_cobol_with_copybooks,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class ASTBuilderError(Exception):
    """Base exception for AST builder errors."""

    pass


class ASTParseError(ASTBuilderError):
    """Raised when COBOL parsing fails."""

    pass


class ASTSerializationError(ASTBuilderError):
    """Raised when AST serialization/deserialization fails."""

    pass


# =============================================================================
# Node Traversal Utilities
# =============================================================================


def find_node(node: ParseNode, type_names: list[str]) -> ParseNode | None:
    """Find a node by type name(s) in the AST.

    Searches the AST depth-first for a node matching any of the given type names.

    Args:
        node: Root node to search from
        type_names: List of type names to match against

    Returns:
        First matching ParseNode, or None if not found
    """
    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        return node
    for child in node.children:
        result = find_node(child, type_names)
        if result:
            return result
    return None


def find_all_nodes(node: ParseNode, type_names: list[str]) -> list[ParseNode]:
    """Find all nodes matching type names in the AST.

    Searches the entire AST for all nodes matching any of the given type names.

    Args:
        node: Root node to search from
        type_names: List of type names to match against

    Returns:
        List of all matching ParseNode instances
    """
    results: list[ParseNode] = []
    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        results.append(node)
    for child in node.children:
        results.extend(find_all_nodes(child, type_names))
    return results


def count_nodes(node: ParseNode) -> int:
    """Count total nodes in the AST.

    Args:
        node: Root node to count from

    Returns:
        Total number of nodes in the tree
    """
    count = 1
    for child in node.children:
        count += count_nodes(child)
    return count


def count_nodes_from_dict(node_dict: dict[str, Any]) -> int:
    """Count total nodes from serialized AST dictionary.

    Args:
        node_dict: Serialized AST as dictionary

    Returns:
        Total number of nodes in the tree
    """
    count = 1
    for child in node_dict.get("children", []):
        count += count_nodes_from_dict(child)
    return count


# =============================================================================
# Program Name and Metadata Extraction
# =============================================================================


def extract_program_name(parse_tree: ParseNode) -> str | None:
    """Extract program name from parse tree.

    Searches for PROGRAM-ID in the IDENTIFICATION DIVISION.

    Args:
        parse_tree: The ParseNode tree

    Returns:
        Program name or None if not found
    """

    def _find_node_recursive(node: ParseNode, target_type: str) -> ParseNode | None:
        if target_type in {node.type, node.rule_name}:
            return node
        for child in node.children:
            result = _find_node_recursive(child, target_type)
            if result:
                return result
        return None

    # Try to find PROGRAM_NAME or programIdParagraph
    program_name_node = _find_node_recursive(parse_tree, "PROGRAM_NAME")
    if program_name_node and program_name_node.value:
        return str(program_name_node.value)

    # Try finding in programIdParagraph
    program_id_node = _find_node_recursive(parse_tree, "programIdParagraph")
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


def extract_metadata(parse_tree: ParseNode, file_path: str | None = None) -> dict[str, Any]:
    """Extract basic metadata from parse tree.

    Args:
        parse_tree: The ParseNode tree
        file_path: Optional source file path

    Returns:
        Dictionary with program_info and basic metrics
    """
    program_name = extract_program_name(parse_tree)

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


# =============================================================================
# Serialization / Deserialization
# =============================================================================


def serialize_parse_node(node: ParseNode) -> dict[str, Any]:
    """Serialize ParseNode to dictionary.

    Args:
        node: ParseNode instance to serialize

    Returns:
        Dictionary representation of ParseNode (uses Pydantic model_dump)
    """
    # Use Pydantic's model_dump for serialization
    # exclude_none=True to avoid cluttering output with None values
    return node.model_dump(exclude_none=True)


def deserialize_parse_node(node_dict: dict[str, Any]) -> ParseNode:
    """Deserialize ParseNode from dictionary.

    Supports both old format (node_type) and new format (type) for
    backward compatibility.

    Args:
        node_dict: Dictionary representation of ParseNode

    Returns:
        ParseNode instance

    Raises:
        ASTSerializationError: If deserialization fails
    """
    try:
        # Support both old format (node_type) and new format (type)
        node_type = node_dict.get("type") or node_dict.get("node_type", "")
        value = node_dict.get("value")
        children = node_dict.get("children", [])

        # Recursively deserialize children
        deserialized_children: list[ParseNode] = []
        for child in children:
            if isinstance(child, dict):
                deserialized_children.append(deserialize_parse_node(child))

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
    except Exception as e:
        raise ASTSerializationError(f"Failed to deserialize ParseNode: {e}") from e


# =============================================================================
# Copybook Resolution
# =============================================================================


def resolve_copybook_paths(
    *,
    copybook_directories: Any,
    file_path: str | None,
) -> list[Path] | None:
    """Resolve copybook directories from explicit input or auto-detection.

    If copybook_directories is provided, uses those. Otherwise, attempts to
    auto-detect copybook directories based on the file_path location.

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


def add_copybook_info_to_metadata(metadata: dict[str, Any], preprocessed: Any | None) -> None:
    """Attach copybook preprocessing info to metadata if available.

    Args:
        metadata: Metadata dictionary to modify
        preprocessed: Preprocessed source object with copybook info
    """
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


def add_copybook_info_to_result(result: dict[str, Any], preprocessed: Any | None) -> None:
    """Attach copybook preprocessing info directly to result if available.

    Args:
        result: Result dictionary to modify
        preprocessed: Preprocessed source object with copybook info
    """
    if not preprocessed:
        return

    result["copybook_info"] = {
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


# =============================================================================
# COBOL Parsing
# =============================================================================


def parse_cobol_source_or_file(
    *,
    source_code: str | None,
    file_path: str | None,
    copybook_paths: list[Path] | None,
) -> tuple[ParseNode, list[Comment], IdentificationMetadata, Any | None]:
    """Parse COBOL from either file or source, optionally with copybook preprocessing.

    This is the primary parsing entry point that handles all parsing scenarios:
    - Source code with or without copybooks
    - File path with or without copybooks

    Args:
        source_code: COBOL source code string (optional if file_path provided)
        file_path: Path to COBOL file (optional if source_code provided)
        copybook_paths: Optional list of directories to search for copybooks

    Returns:
        Tuple of (parsed_tree, comments, id_metadata, preprocessed)
        - parsed_tree: ParseNode representing the AST
        - comments: List of Comment objects
        - id_metadata: IdentificationMetadata with AUTHOR, DATE-WRITTEN, etc.
        - preprocessed: PreprocessedSource object or None

    Raises:
        ValueError: If neither source_code nor file_path is provided
        SyntaxError: If COBOL parsing fails
        FileNotFoundError: If file_path doesn't exist
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


# =============================================================================
# Result Persistence
# =============================================================================


def save_ast_result(
    tool_name: str,
    result: dict[str, Any],
    source_identifier: str | None = None,
) -> Path | None:
    """Save AST/tool execution result to tests/cobol_samples/result directory.

    Args:
        tool_name: Name of the tool (e.g., "build_ast", "parse_cobol")
        result: Tool execution result dictionary
        source_identifier: Optional identifier for the source (e.g., program name)

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


# =============================================================================
# Main AST Building Function
# =============================================================================


def build_ast(  # noqa: PLR0912
    *,
    source_code: str | None = None,
    file_path: str | None = None,
    copybook_directories: list[str] | None = None,
    include_comments: bool = True,
    include_metadata: bool = True,
    save_result: bool = True,
) -> dict[str, Any]:
    """Build Abstract Syntax Tree (AST) from COBOL source code.

    This is the main entry point for AST building. It parses COBOL source code
    and returns a comprehensive AST representation suitable for further analysis.

    The AST (ParseNode structure) serves as the foundation for:
    - ASG (Abstract Semantic Graph) building
    - CFG (Control Flow Graph) building
    - DFG (Data Flow Graph) building
    - Call graph generation

    Args:
        source_code: COBOL source code as string (optional if file_path provided)
        file_path: Path to COBOL source file (optional if source_code provided)
        copybook_directories: Optional list of directories to search for copybooks
        include_comments: Include extracted comments in output (default: True)
        include_metadata: Include IDENTIFICATION DIVISION metadata (default: True)
        save_result: Save result to file (default: True)

    Returns:
        Dictionary with AST representation including:
        - success: Whether parsing succeeded
        - ast: Complete AST structure as nested dictionary
        - parse_tree: The ParseNode object (for programmatic use)
        - program_name: Extracted program name
        - node_count: Total number of nodes in the AST
        - root_type: Type of the root AST node
        - metadata: Dependencies (calls, copybooks, files)
        - comments: List of extracted comments (if include_comments=True)
        - comment_count: Number of comments (if include_comments=True)
        - identification_metadata: AUTHOR, DATE-WRITTEN, etc. (if include_metadata=True)
        - copybook_info: Copybook resolution details
        - source_file: Path to source file (if file_path provided)
        - saved_to: Path where result was saved (if save_result=True)

    Raises:
        ASTParseError: If parsing fails
    """
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

        # Resolve copybook paths
        copybook_paths = resolve_copybook_paths(
            copybook_directories=copybook_directories,
            file_path=file_path if isinstance(file_path, str) else None,
        )

        # Parse COBOL source
        parsed_tree, comments, id_metadata, preprocessed = parse_cobol_source_or_file(
            source_code=source_code if isinstance(source_code, str) else None,
            file_path=file_path if isinstance(file_path, str) else None,
            copybook_paths=copybook_paths,
        )

        # Serialize AST
        ast_dict = serialize_parse_node(parsed_tree)

        # Extract program name
        program_name = extract_program_name(parsed_tree)

        # Extract metadata (dependencies)
        metadata = extract_metadata(parsed_tree, file_path)

        # Add copybook info to metadata
        add_copybook_info_to_metadata(metadata, preprocessed)

        # Count nodes
        node_count = count_nodes_from_dict(ast_dict)

        # Build result
        result: dict[str, Any] = {
            "success": True,
            "ast": ast_dict,
            "parse_tree": parsed_tree,  # Include ParseNode for programmatic use
            "program_name": program_name,
            "node_count": node_count,
            "root_type": parsed_tree.type,
            "metadata": metadata,
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

        # Include identification metadata if requested
        if include_metadata and id_metadata:
            id_metadata_dict: dict[str, Any] = {}
            if id_metadata.author:
                id_metadata_dict["author"] = id_metadata.author
            if id_metadata.installation:
                id_metadata_dict["installation"] = id_metadata.installation
            if id_metadata.date_written:
                id_metadata_dict["date_written"] = id_metadata.date_written
            if id_metadata.date_compiled:
                id_metadata_dict["date_compiled"] = id_metadata.date_compiled
            if id_metadata.security:
                id_metadata_dict["security"] = id_metadata.security
            if id_metadata.remarks:
                id_metadata_dict["remarks"] = id_metadata.remarks
            if id_metadata_dict:
                result["identification_metadata"] = id_metadata_dict

        # Add copybook info at top level
        if preprocessed:
            add_copybook_info_to_result(result, preprocessed)

        # Add source file info
        if file_path:
            result["source_file"] = file_path

        # Save result to file
        if save_result:
            saved_path = save_ast_result("build_ast", result, program_name)
            if saved_path:
                result["saved_to"] = str(saved_path)

        return result

    except SyntaxError as e:
        logger.warning(f"COBOL syntax error: {e}")
        raise ASTParseError(f"COBOL syntax error: {e}") from e
    except FileNotFoundError as e:
        raise ASTParseError(str(e)) from e
    except Exception as e:
        logger.exception("Failed to build AST")
        raise ASTParseError(f"Failed to build AST: {e}") from e

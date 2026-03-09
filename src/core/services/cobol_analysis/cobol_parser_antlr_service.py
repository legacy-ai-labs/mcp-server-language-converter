"""COBOL parser service using ANTLR4.

This module provides COBOL parsing capabilities using ANTLR4 with the official
Cobol85 grammar from antlr/grammars-v4. The parser converts ANTLR parse trees
to our ParseNode format for ASG (Abstract Semantic Graph) construction.

The ParseNode structure enables:
- JSON serialization for debugging and analysis
- ASG construction via asg_builder_service.py
- CFG/DFG/PDG analysis from the same structure

Includes preprocessing to handle:
- AUTHOR, DATE-WRITTEN, INSTALLATION, SECURITY, REMARKS paragraphs
- COPY statement expansion (via CobolPreprocessor integration)
- REPLACE directive processing

For files with COPY statements, use `parse_cobol_file_with_copybooks()` which
integrates the full preprocessor for copybook resolution.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from antlr4 import CommonTokenStream, InputStream
from antlr4.tree.Tree import TerminalNode
from pydantic import BaseModel, Field

from src.core.services.cobol_analysis.antlr_cobol.grammars.Cobol85Lexer import Cobol85Lexer
from src.core.services.cobol_analysis.antlr_cobol.grammars.Cobol85Parser import Cobol85Parser
from src.core.services.cobol_analysis.cobol_preprocessor_service import (
    CobolPreprocessor,
    PreprocessedSource,
    PreprocessorConfig,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Source Location and Comments (formerly in cobol_analysis_model.py)
# =============================================================================


class SourceLocation(BaseModel):
    """Represents a source code location.

    Used for tracking positions in COBOL source code for error reporting,
    cross-references, and source reconstruction.
    """

    line: int = Field(description="Line number (1-based)")
    column: int | None = Field(default=None, description="Column number (0-based)")
    file_path: str | None = Field(default=None, description="Source file path")

    def __str__(self) -> str:
        """String representation of source location."""
        if self.file_path:
            return f"{self.file_path}:{self.line}"
        return f"line {self.line}"


class CommentType(str, Enum):
    """Types of comments in COBOL code."""

    LINE = "LINE"  # Single-line comment (*)
    HEADER = "HEADER"  # Header block comment
    SECTION = "SECTION"  # Section separator comment
    INLINE = "INLINE"  # Comment on same line as code
    TODO = "TODO"  # TODO/FIXME/XXX comments
    DOCUMENTATION = "DOCUMENTATION"  # Documentation comments


class Comment(BaseModel):
    """Represents a comment in COBOL source code.

    Comments preserve business context, intent, and documentation that would
    otherwise be lost in a basic AST. This enables higher quality code
    conversion and user story generation.
    """

    text: str = Field(description="Comment text (without leading * or other markers)")
    location: SourceLocation = Field(description="Where the comment appears")
    comment_type: CommentType = Field(default=CommentType.LINE, description="Type of comment")

    def __str__(self) -> str:
        """String representation of comment."""
        return f"* {self.text}"


# =============================================================================
# ParseNode - AST structure for COBOL parsing
# =============================================================================


class ParseNode(BaseModel):
    """Parse tree node representing COBOL AST structure.

    This structure is used by the ASG builder to construct the Abstract Semantic
    Graph. It supports JSON serialization for debugging and analysis.

    The node can represent either:
    - A rule node (internal node with children)
    - A terminal node (leaf node with token value)

    Attributes:
    - id: Unique node identifier
    - type: ANTLR class name (e.g., "StartRule", "TerminalNodeImpl")
    - rule_index: ANTLR rule index (for rule nodes)
    - rule_name: ANTLR rule name (for rule nodes)
    - start_line, start_column: Start position in source
    - end_line, end_column: End position in source
    - children: Child nodes (for rule nodes)
    - text: Token text (for terminal nodes)
    - token_type: Token type number (for terminal nodes)
    - token_name: Token symbolic name (for terminal nodes)
    - value: Extracted semantic value (e.g., program name, paragraph name)
    """

    # Node identity
    id: int | None = Field(default=None, description="Unique node identifier")
    type: str = Field(description="Node type (ANTLR class name or rule name)")

    # Rule node fields
    rule_index: int | None = Field(default=None, description="ANTLR rule index")
    rule_name: str | None = Field(default=None, description="ANTLR rule name")

    # Source location
    start_line: int | None = Field(default=None, description="Start line (1-based)")
    start_column: int | None = Field(default=None, description="Start column (0-based)")
    end_line: int | None = Field(default=None, description="End line (1-based)")
    end_column: int | None = Field(default=None, description="End column (0-based)")

    # Children (for rule nodes)
    children: list[ParseNode] = Field(default_factory=list, description="Child nodes")

    # Terminal node fields
    text: str | None = Field(default=None, description="Token text (for terminals)")
    token_type: int | None = Field(default=None, description="Token type number (for terminals)")
    token_name: str | None = Field(default=None, description="Token symbolic name (for terminals)")

    # Semantic value (extracted from structure)
    value: Any | None = Field(
        default=None,
        description="Extracted semantic value (e.g., program name, identifier)",
    )

    # Legacy compatibility aliases (read-only properties)
    @property
    def node_type(self) -> str:
        """Legacy alias for 'type' field (for backward compatibility)."""
        return self.type

    @property
    def line_number(self) -> int | None:
        """Legacy alias for 'start_line' field (for backward compatibility)."""
        return self.start_line

    @property
    def column_number(self) -> int | None:
        """Legacy alias for 'start_column' field (for backward compatibility)."""
        return self.start_column

    def __repr__(self) -> str:
        """String representation for debugging."""
        if self.value is not None:
            return f"{self.type}({self.value})"
        if self.text is not None:
            return f"{self.type}({self.text!r})"
        if self.children:
            return f"{self.type}({len(self.children)} children)"
        return self.type

    def is_terminal(self) -> bool:
        """Check if this is a terminal node (token)."""
        return self.text is not None

    def is_rule(self) -> bool:
        """Check if this is a rule node (has children)."""
        return self.rule_name is not None

    model_config = {"extra": "allow"}


# =============================================================================
# Identification Metadata
# =============================================================================


@dataclass
class IdentificationMetadata:
    """Metadata extracted from IDENTIFICATION DIVISION optional paragraphs.

    These paragraphs (AUTHOR, DATE-WRITTEN, etc.) use plain text in real COBOL
    but the ANTLR grammar expects '*>CE' tagged comment entries. We extract
    them via preprocessing before parsing.
    """

    author: str | None = None
    installation: str | None = None
    date_written: str | None = None
    date_compiled: str | None = None
    security: str | None = None
    remarks: str | None = None
    source_lines: dict[str, int] = field(default_factory=dict)  # paragraph -> line number


# Regex patterns for optional IDENTIFICATION DIVISION paragraphs
# These match: AUTHOR. some text [more text] [until next paragraph or division]
_ID_PARAGRAPH_PATTERNS = {
    "author": re.compile(
        r"^\s*AUTHOR\s*\.\s*(.*?)(?=^\s*(?:INSTALLATION|DATE-WRITTEN|DATE-COMPILED|SECURITY|REMARKS|ENVIRONMENT|DATA|PROCEDURE)\b|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    "installation": re.compile(
        r"^\s*INSTALLATION\s*\.\s*(.*?)(?=^\s*(?:AUTHOR|DATE-WRITTEN|DATE-COMPILED|SECURITY|REMARKS|ENVIRONMENT|DATA|PROCEDURE)\b|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    "date_written": re.compile(
        r"^\s*DATE-WRITTEN\s*\.\s*(.*?)(?=^\s*(?:AUTHOR|INSTALLATION|DATE-COMPILED|SECURITY|REMARKS|ENVIRONMENT|DATA|PROCEDURE)\b|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    "date_compiled": re.compile(
        r"^\s*DATE-COMPILED\s*\.\s*(.*?)(?=^\s*(?:AUTHOR|INSTALLATION|DATE-WRITTEN|SECURITY|REMARKS|ENVIRONMENT|DATA|PROCEDURE)\b|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    "security": re.compile(
        r"^\s*SECURITY\s*\.\s*(.*?)(?=^\s*(?:AUTHOR|INSTALLATION|DATE-WRITTEN|DATE-COMPILED|REMARKS|ENVIRONMENT|DATA|PROCEDURE)\b|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    "remarks": re.compile(
        r"^\s*REMARKS\s*\.\s*(.*?)(?=^\s*(?:AUTHOR|INSTALLATION|DATE-WRITTEN|DATE-COMPILED|SECURITY|ENVIRONMENT|DATA|PROCEDURE)\b|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
}

# Pattern to match and remove entire optional paragraphs
_ID_PARAGRAPH_REMOVAL_PATTERN = re.compile(
    r"^\s*(AUTHOR|INSTALLATION|DATE-WRITTEN|DATE-COMPILED|SECURITY|REMARKS)\s*\.\s*"
    r"(.*?)(?=^\s*(?:AUTHOR|INSTALLATION|DATE-WRITTEN|DATE-COMPILED|SECURITY|REMARKS|ENVIRONMENT|DATA|PROCEDURE)\b|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


def _extract_identification_metadata(source: str) -> IdentificationMetadata:
    """Extract metadata from IDENTIFICATION DIVISION optional paragraphs.

    Extracts AUTHOR, INSTALLATION, DATE-WRITTEN, DATE-COMPILED, SECURITY, and
    REMARKS paragraphs from the source code before they are stripped for parsing.

    Args:
        source: COBOL source code

    Returns:
        IdentificationMetadata with extracted values
    """
    metadata = IdentificationMetadata()

    # Track line numbers for each paragraph
    lines = source.split("\n")
    for line_num, line in enumerate(lines, start=1):
        line_upper = line.upper().strip()
        for para_name in [
            "AUTHOR",
            "INSTALLATION",
            "DATE-WRITTEN",
            "DATE-COMPILED",
            "SECURITY",
            "REMARKS",
        ]:
            if line_upper.startswith(para_name):
                # Normalize to field name format
                field_name = para_name.lower().replace("-", "_")
                metadata.source_lines[field_name] = line_num

    # Extract each paragraph's content
    for field_name, pattern in _ID_PARAGRAPH_PATTERNS.items():
        match = pattern.search(source)
        if match:
            # Clean up the extracted text
            content = match.group(1).strip()
            # Remove comment markers (* in column 7) and *>CE tags and clean up
            content_lines = []
            for line in content.split("\n"):
                # Skip pure comment lines but include content after AUTHOR.
                stripped = line.strip()
                # Strip *>CE comment entry tag added by CobolPreprocessor
                if stripped.startswith("*>CE"):
                    stripped = stripped[4:].strip()
                if stripped and not stripped.startswith("*"):
                    content_lines.append(stripped)
            if content_lines:
                setattr(metadata, field_name, " ".join(content_lines))

    return metadata


def _preprocess_cobol_source(source: str) -> tuple[str, IdentificationMetadata]:
    """Preprocess COBOL source to handle optional IDENTIFICATION paragraphs.

    The ANTLR Cobol85 grammar expects commentEntry lines to start with '*>CE' tag,
    but real COBOL uses plain text for AUTHOR, DATE-WRITTEN, etc. This function:
    1. Extracts metadata from these paragraphs
    2. Removes them from the source so ANTLR can parse successfully

    Args:
        source: Original COBOL source code

    Returns:
        Tuple of (preprocessed source, extracted metadata)
    """
    # First extract metadata
    metadata = _extract_identification_metadata(source)

    # Remove optional paragraphs from source
    # Replace with empty lines to preserve line numbers for error messages
    def replace_with_blanks(match: re.Match[str]) -> str:
        """Replace matched text with blank lines to preserve line numbers."""
        text = match.group(0)
        num_lines = text.count("\n")
        return "\n" * num_lines

    preprocessed = _ID_PARAGRAPH_REMOVAL_PATTERN.sub(replace_with_blanks, source)

    if metadata.author or metadata.date_written or metadata.installation:
        logger.debug(
            f"Preprocessed COBOL: extracted metadata (author={metadata.author}, "
            f"date_written={metadata.date_written})"
        )

    return preprocessed, metadata


# =============================================================================
# Node ID Counter for AST Generation
# =============================================================================

_node_id_counter = {"value": 0}


def _reset_node_id_counter() -> None:
    """Reset the node ID counter (call before parsing a new file)."""
    _node_id_counter["value"] = 0


def _get_next_node_id() -> int:
    """Get the next node ID and increment the counter."""
    current = _node_id_counter["value"]
    _node_id_counter["value"] = current + 1
    return current


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_value_from_children(children: list[ParseNode]) -> str | None:
    """Recursively extract string value from ParseNode children.

    This function searches through children (and their descendants) to find
    the first terminal node with a text value (for terminals) or value field.

    Args:
        children: List of ParseNode children to search

    Returns:
        First non-None string value found, or None if no value exists
    """
    if not children:
        return None

    for child in children:
        # Check for terminal node text
        if child.text is not None and isinstance(child.text, str):
            return child.text

        # Check for explicit value on this child
        if child.value is not None and isinstance(child.value, str):
            return str(child.value)

        # Recursively search grandchildren
        if child.children:
            value = _extract_value_from_children(child.children)
            if value is not None:
                return value

    return None


def _antlr_to_parse_node(tree: Any, parser: Cobol85Parser) -> ParseNode:
    """Convert ANTLR parse tree to ParseNode format.

    Creates ParseNode objects with all fields populated for ASG construction
    and JSON serialization.

    Args:
        tree: ANTLR parse tree node (RuleContext or TerminalNode)
        parser: Cobol85Parser instance for accessing rule names

    Returns:
        ParseNode with complete structure for ASG building
    """
    # Terminal node (leaf) - has token value
    if isinstance(tree, TerminalNode):
        # ANTLR4 Python TerminalNode has getSymbol() method
        get_symbol = getattr(tree, "getSymbol", None)
        if get_symbol is None:
            raise ValueError("TerminalNode has no getSymbol method")
        symbol = get_symbol()

        # Get token symbolic name
        token_name = (
            parser.symbolicNames[symbol.type]
            if symbol.type < len(parser.symbolicNames) and parser.symbolicNames[symbol.type]
            else None
        )

        # Create terminal node
        return ParseNode(
            id=_get_next_node_id(),
            type="TerminalNodeImpl",
            text=symbol.text,
            start_line=symbol.line,
            start_column=symbol.column,
            token_type=symbol.type,
            token_name=token_name,
        )

    # Rule node (internal) - has children
    rule_index = tree.getRuleIndex()
    rule_name = parser.ruleNames[rule_index]

    # Get source location
    start_line = tree.start.line if hasattr(tree, "start") and tree.start else None
    start_column = tree.start.column if hasattr(tree, "start") and tree.start else None
    end_line = tree.stop.line if hasattr(tree, "stop") and tree.stop else None
    end_column = tree.stop.column if hasattr(tree, "stop") and tree.stop else None

    # Convert children recursively
    children = (
        [_antlr_to_parse_node(child, parser) for child in tree.children] if tree.children else []
    )

    # Get type name (capitalized rule name)
    type_name = rule_name[0].upper() + rule_name[1:] if rule_name else "Unknown"

    # Special handling for some nodes to extract semantic values
    value = None
    if rule_name in ["programName", "paragraphName", "procedureName", "dataName", "fileName"]:
        # Extract identifier value from children (recursively if needed)
        value = _extract_value_from_children(children)

    # Create rule node
    return ParseNode(
        id=_get_next_node_id(),
        type=type_name,
        rule_index=rule_index,
        rule_name=rule_name,
        start_line=start_line,
        start_column=start_column,
        end_line=end_line,
        end_column=end_column,
        children=children,
        value=value,
    )


def _normalize_node_names(node: ParseNode) -> ParseNode:
    """Normalize ANTLR node names to match PLY parser format.

    ANTLR uses: IdentificationDivision, DataDivision, ProcedureDivision
    PLY uses: IDENTIFICATION_DIVISION, DATA_DIVISION, PROCEDURE_DIVISION

    Since ParseNode is a Pydantic model (immutable by default), this returns
    a new node with normalized names.

    Args:
        node: ParseNode to normalize

    Returns:
        New ParseNode with normalized names
    """
    # Mapping of ANTLR names (various cases) to PLY names
    name_map = {
        # Divisions and sections (handle various case formats)
        "IdentificationDivision": "IDENTIFICATION_DIVISION",
        "DataDivision": "DATA_DIVISION",
        "ProcedureDivision": "PROCEDURE_DIVISION",
        "EnvironmentDivision": "ENVIRONMENT_DIVISION",
        "WorkingStorageSection": "WORKING_STORAGE_SECTION",
        "LinkageSection": "LINKAGE_SECTION",
        "FileSection": "FILE_SECTION",
        "ProgramIdParagraph": "PROGRAM_ID_PARAGRAPH",
        "ProgramName": "PROGRAM_NAME",
        "ParagraphName": "PARAGRAPH_NAME",
        "ProcedureDivisionBody": "PROCEDURE_BODY",
        # Statement types
        "MoveStatement": "MOVE_STATEMENT",
        "PerformStatement": "PERFORM_STATEMENT",
        "IfStatement": "IF_STATEMENT",
        "IfElseStatement": "IF_ELSE_STATEMENT",
        "CallStatement": "CALL_STATEMENT",
        "ComputeStatement": "COMPUTE_STATEMENT",
        "ReadStatement": "READ_STATEMENT",
        "WriteStatement": "WRITE_STATEMENT",
        "OpenStatement": "OPEN_STATEMENT",
        "CloseStatement": "CLOSE_STATEMENT",
        "DisplayStatement": "DISPLAY_STATEMENT",
        "AddStatement": "ADD_STATEMENT",
        "EvaluateStatement": "EVALUATE_STATEMENT",
        "ExitStatement": "EXIT_STATEMENT",
        "StopStatement": "STOP_STATEMENT",
        "GoToStatement": "GOTO_STATEMENT",
        "GotoStatement": "GOTO_STATEMENT",
        # Also handle uppercase versions
        "IDENTIFICATIONDIVISION": "IDENTIFICATION_DIVISION",
        "DATADIVISION": "DATA_DIVISION",
        "PROCEDUREDIVISION": "PROCEDURE_DIVISION",
        "ENVIRONMENTDIVISION": "ENVIRONMENT_DIVISION",
        "WORKINGSTORAGESECTION": "WORKING_STORAGE_SECTION",
        "LINKAGESECTION": "LINKAGE_SECTION",
        "FILESECTION": "FILE_SECTION",
        "PROGRAMIDPARAGRAPH": "PROGRAM_ID_PARAGRAPH",
        "PROGRAMNAME": "PROGRAM_NAME",
        "PARAGRAPHNAME": "PARAGRAPH_NAME",
        "PROCEDUREDIVISIONBODY": "PROCEDURE_BODY",
    }

    # Normalize type name: explicit map first, then fall back to ALLUPPERCASE
    # (the ASG builder expects ALLUPPERCASE for all node types not explicitly mapped)
    new_type = name_map.get(node.type, node.type.upper())

    # Recursively normalize children
    new_children = [_normalize_node_names(child) for child in node.children]

    # Create new node with normalized values
    return ParseNode(
        id=node.id,
        type=new_type,
        rule_index=node.rule_index,
        rule_name=node.rule_name,
        start_line=node.start_line,
        start_column=node.start_column,
        end_line=node.end_line,
        end_column=node.end_column,
        children=new_children,
        text=node.text,
        token_type=node.token_type,
        token_name=node.token_name,
        value=node.value,
    )


def _classify_comment_type(text: str) -> CommentType:
    """Classify a comment based on its content and format.

    Args:
        text: Comment text (without leading * or other markers)

    Returns:
        CommentType enum value
    """
    text_upper = text.upper().strip()

    # Check for TODO/FIXME/XXX markers
    if any(marker in text_upper for marker in ["TODO", "FIXME", "XXX", "HACK", "BUG"]):
        return CommentType.TODO

    # Check for header block patterns (stars, equals, dashes)
    if any(char * 5 in text for char in ["*", "=", "-", "#"]):
        return CommentType.HEADER

    # Check for section separators
    if text_upper.startswith("===") or text_upper.startswith("---"):
        return CommentType.SECTION

    # Check for documentation keywords
    doc_keywords = [
        "PURPOSE:",
        "DESCRIPTION:",
        "AUTHOR:",
        "INPUT:",
        "OUTPUT:",
        "RETURNS:",
        "PARAMS:",
        "NOTE:",
        "WARNING:",
        "IMPORTANT:",
        "CRITICAL:",
    ]
    if any(keyword in text_upper for keyword in doc_keywords):
        return CommentType.DOCUMENTATION

    # Default to line comment
    return CommentType.LINE


def _extract_comments_from_token_stream(token_stream: CommonTokenStream) -> list[Comment]:
    """Extract all comments from ANTLR token stream.

    COBOL comments in ANTLR are typically sent to a hidden channel.
    This function retrieves them and converts to Comment objects.

    Args:
        token_stream: CommonTokenStream from ANTLR lexer

    Returns:
        List of Comment objects with full source location info
    """
    comments: list[Comment] = []

    # Get all tokens (including hidden channel tokens)
    token_stream.fill()
    all_tokens = token_stream.tokens

    for token in all_tokens:
        # COBOL comments are typically on channel 1 (hidden)
        # Token type varies - check for COMMENTLINE or similar
        if token.channel == 1:  # Hidden channel (comments)
            # Extract comment text
            text = token.text.strip()

            # Remove leading comment markers (* or other variations)
            if text.startswith("*"):
                text = text[1:].strip()
            elif text.startswith("//"):
                text = text[2:].strip()

            # Create source location
            location = SourceLocation(
                line=token.line, column=token.column if hasattr(token, "column") else None
            )

            # Classify comment type
            comment_type = _classify_comment_type(text)

            # Create Comment object
            comment = Comment(text=text, location=location, comment_type=comment_type)
            comments.append(comment)

    logger.debug(f"Extracted {len(comments)} comments from token stream")
    return comments


def _extract_program_node(parse_tree: ParseNode) -> ParseNode:
    """Extract PROGRAMUNIT node and rename to PROGRAM for compatibility.

    The ANTLR parser produces: StartRule -> CompilationUnit -> ProgramUnit
    But the AST builder expects: PROGRAM (root node)

    Since ParseNode is a Pydantic model, this returns a new node with
    the type changed to PROGRAM and all node names normalized.

    Args:
        parse_tree: ANTLR parse tree with StartRule root

    Returns:
        ProgramUnit node renamed to PROGRAM with normalized node names

    Raises:
        SyntaxError: If expected structure is not found
    """
    # Navigate: StartRule -> CompilationUnit -> ProgramUnit
    # Handle both capitalized and uppercase node type names
    root_type = parse_tree.type
    if root_type not in ("StartRule", "STARTRULE", "startRule"):
        raise SyntaxError(f"Expected StartRule root, got {root_type}")

    # Find CompilationUnit child
    compilation_unit: ParseNode | None = None
    for child in parse_tree.children:
        if isinstance(child, ParseNode) and child.type in (
            "CompilationUnit",
            "COMPILATIONUNIT",
            "compilationUnit",
        ):
            compilation_unit = child
            break

    if not compilation_unit:
        raise SyntaxError("No CompilationUnit found in parse tree")

    # Find ProgramUnit child
    program_unit: ParseNode | None = None
    for child in compilation_unit.children:
        if isinstance(child, ParseNode) and child.type in (
            "ProgramUnit",
            "PROGRAMUNIT",
            "programUnit",
        ):
            program_unit = child
            break

    if not program_unit:
        raise SyntaxError("No ProgramUnit found in CompilationUnit")

    # Create new node with type changed to PROGRAM
    program_node = ParseNode(
        id=program_unit.id,
        type="PROGRAM",
        rule_index=program_unit.rule_index,
        rule_name=program_unit.rule_name,
        start_line=program_unit.start_line,
        start_column=program_unit.start_column,
        end_line=program_unit.end_line,
        end_column=program_unit.end_column,
        children=program_unit.children,
        text=program_unit.text,
        token_type=program_unit.token_type,
        token_name=program_unit.token_name,
        value=program_unit.value,
    )

    # Normalize all node names in the tree to match PLY format
    normalized_program = _normalize_node_names(program_node)

    return normalized_program


def parse_cobol(
    source: str,
) -> tuple[ParseNode, list[Comment], IdentificationMetadata]:
    """Parse COBOL source code and return parse tree with comments (full-fidelity).

    Includes preprocessing to handle AUTHOR, DATE-WRITTEN, INSTALLATION, SECURITY,
    and REMARKS paragraphs which use plain text in real COBOL but the ANTLR grammar
    expects '*>CE' tagged comment entries. These are extracted as metadata.

    Args:
        source: COBOL source code as string

    Returns:
        Tuple of:
        - ParseNode representing program structure
        - List of Comment objects
        - IdentificationMetadata with AUTHOR, DATE-WRITTEN, etc.

    Raises:
        SyntaxError: If parsing fails
    """
    try:
        # Reset node ID counter for this parse
        _reset_node_id_counter()

        # Preprocess to extract and remove optional ID division paragraphs
        preprocessed_source, id_metadata = _preprocess_cobol_source(source)

        # Create input stream from preprocessed source (uppercase for case-insensitivity)
        input_stream = InputStream(preprocessed_source.upper())

        # Create lexer and token stream
        lexer = Cobol85Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)

        # Create parser
        parser = Cobol85Parser(token_stream)

        # Parse the program (startRule is the top-level rule)
        tree = parser.startRule()  # type: ignore[no-untyped-call]

        # Check for syntax errors
        if parser.getNumberOfSyntaxErrors() > 0:
            error_msg = f"Parsing failed with {parser.getNumberOfSyntaxErrors()} syntax error(s)"
            logger.error(error_msg)
            raise SyntaxError(error_msg)

        # Extract comments from token stream (full-fidelity)
        comments = _extract_comments_from_token_stream(token_stream)

        # Convert ANTLR tree to ParseNode
        parse_node = _antlr_to_parse_node(tree, parser)

        # Transform to compatible format for AST builder
        # ANTLR: STARTRULE -> COMPILATIONUNIT -> PROGRAMUNIT
        # Expected: PROGRAM (root)
        program_node = _extract_program_node(parse_node)

        logger.info(f"COBOL parsing successful (ANTLR) - {len(comments)} comments extracted")
        return program_node, comments, id_metadata

    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise SyntaxError(f"Failed to parse COBOL: {e}") from e


def parse_cobol_file(
    file_path: str,
) -> tuple[ParseNode, list[Comment], IdentificationMetadata]:
    """Parse a COBOL file and return parse tree with comments (full-fidelity).

    Includes preprocessing to handle AUTHOR, DATE-WRITTEN, INSTALLATION, SECURITY,
    and REMARKS paragraphs which use plain text in real COBOL but the ANTLR grammar
    expects '*>CE' tagged comment entries. These are extracted as metadata.

    Args:
        file_path: Path to COBOL source file

    Returns:
        Tuple of:
        - ParseNode representing program structure
        - List of Comment objects
        - IdentificationMetadata with AUTHOR, DATE-WRITTEN, etc.

    Raises:
        FileNotFoundError: If file doesn't exist
        SyntaxError: If parsing fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"COBOL file not found: {file_path}")

    logger.info(f"Parsing COBOL file: {file_path}")

    try:
        # Reset node ID counter for this parse
        _reset_node_id_counter()

        # Read source and preprocess
        source = path.read_text(encoding="utf-8")
        preprocessed_source, id_metadata = _preprocess_cobol_source(source)

        # Create input stream from preprocessed source (uppercase for case-insensitivity)
        input_stream = InputStream(preprocessed_source.upper())

        # Create lexer and token stream
        lexer = Cobol85Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)

        # Create parser
        parser = Cobol85Parser(token_stream)

        # Parse the program
        tree = parser.startRule()  # type: ignore[no-untyped-call]

        # Check for syntax errors
        if parser.getNumberOfSyntaxErrors() > 0:
            error_msg = f"Parsing failed with {parser.getNumberOfSyntaxErrors()} syntax error(s)"
            logger.error(error_msg)
            raise SyntaxError(error_msg)

        # Extract comments from token stream (full-fidelity)
        comments = _extract_comments_from_token_stream(token_stream)

        # Convert ANTLR tree to ParseNode
        parse_node = _antlr_to_parse_node(tree, parser)

        # Transform to compatible format for AST builder
        program_node = _extract_program_node(parse_node)

        logger.info(
            f"Successfully parsed COBOL file: {file_path} - {len(comments)} comments extracted"
        )
        return program_node, comments, id_metadata

    except Exception as e:
        logger.error(f"Failed to parse file {file_path}: {e}")
        raise SyntaxError(f"Failed to parse COBOL: {e}") from e


def _reset_parser() -> None:
    """Reset parser state (for testing).

    Note: ANTLR parsers are stateless, so this is a no-op.
    Provided for compatibility with PLY parser interface.
    """
    pass


# =============================================================================
# Parser with Full Preprocessor (COPY/REPLACE support)
# =============================================================================


def parse_cobol_file_with_copybooks(
    file_path: str,
    copybook_directories: list[Path] | None = None,
) -> tuple[ParseNode, list[Comment], IdentificationMetadata, PreprocessedSource]:
    """Parse a COBOL file with full preprocessing including COPY statement expansion.

    This function integrates the CobolPreprocessor to resolve COPY statements
    before parsing. Use this for COBOL files that contain COPY directives.

    Args:
        file_path: Path to COBOL source file
        copybook_directories: List of directories to search for copybooks.
            If None, defaults to parent directory and common copybook locations.

    Returns:
        Tuple of:
        - ParseNode representing program structure
        - List of Comment objects
        - IdentificationMetadata with AUTHOR, DATE-WRITTEN, etc.
        - PreprocessedSource with copybook usage tracking

    Raises:
        FileNotFoundError: If file doesn't exist
        SyntaxError: If parsing fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"COBOL file not found: {file_path}")

    logger.info(f"Parsing COBOL file with copybooks: {file_path}")

    # Setup copybook directories
    if copybook_directories is None:
        # Default: check parent directory and common copybook locations
        copybook_directories = []
        parent = path.parent
        copybook_directories.append(parent)

        # Common copybook directory names
        for name in ["copybooks", "copy", "copybook", "COPYBOOKS", "COPY"]:
            candidate = parent / name
            if candidate.exists():
                copybook_directories.append(candidate)
            # Also check sibling directory
            candidate = parent.parent / name
            if candidate.exists():
                copybook_directories.append(candidate)

    # Create preprocessor config
    config = PreprocessorConfig(
        copybook_directories=copybook_directories,
        expand_copy_statements=True,
        process_replace_directives=True,
        remove_comment_lines=True,
    )

    # Run preprocessor
    preprocessor = CobolPreprocessor(config)
    preprocessed = preprocessor.process_file(path)

    if preprocessed.has_errors:
        logger.warning(f"Preprocessor warnings: {preprocessed.errors}")

    # Now parse the preprocessed source
    try:
        # Reset node ID counter for this parse
        _reset_node_id_counter()

        # Extract ID metadata from preprocessed source
        preprocessed_source, id_metadata = _preprocess_cobol_source(preprocessed.source)

        # Create input stream (uppercase for case-insensitivity)
        input_stream = InputStream(preprocessed_source.upper())

        # Create lexer and token stream
        lexer = Cobol85Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)

        # Create parser
        parser = Cobol85Parser(token_stream)

        # Parse the program
        tree = parser.startRule()  # type: ignore[no-untyped-call]

        # Check for syntax errors
        if parser.getNumberOfSyntaxErrors() > 0:
            error_msg = f"Parsing failed with {parser.getNumberOfSyntaxErrors()} syntax error(s)"
            logger.error(error_msg)
            raise SyntaxError(error_msg)

        # Extract comments from token stream
        comments = _extract_comments_from_token_stream(token_stream)

        # Convert ANTLR tree to ParseNode
        parse_node = _antlr_to_parse_node(tree, parser)

        # Transform to compatible format for AST builder
        program_node = _extract_program_node(parse_node)

        logger.info(
            f"Successfully parsed COBOL file with copybooks: {file_path} - "
            f"{len(preprocessed.copybook_usages)} copybooks resolved"
        )
        return program_node, comments, id_metadata, preprocessed

    except Exception as e:
        logger.error(f"Failed to parse file {file_path}: {e}")
        raise SyntaxError(f"Failed to parse COBOL: {e}") from e


def parse_cobol_with_copybooks(
    source: str,
    copybook_directories: list[Path] | None = None,
) -> tuple[ParseNode, list[Comment], IdentificationMetadata, PreprocessedSource]:
    """Parse COBOL source code with full preprocessing including COPY statement expansion.

    This function integrates the CobolPreprocessor to resolve COPY statements
    before parsing. Use this for COBOL source that contains COPY directives.

    Args:
        source: COBOL source code as string
        copybook_directories: List of directories to search for copybooks.

    Returns:
        Tuple of:
        - ParseNode representing program structure
        - List of Comment objects
        - IdentificationMetadata with AUTHOR, DATE-WRITTEN, etc.
        - PreprocessedSource with copybook usage tracking

    Raises:
        SyntaxError: If parsing fails
    """
    logger.info("Parsing COBOL source with copybook support")

    # Create preprocessor config
    config = PreprocessorConfig(
        copybook_directories=copybook_directories or [],
        expand_copy_statements=True,
        process_replace_directives=True,
        remove_comment_lines=True,
    )

    # Run preprocessor
    preprocessor = CobolPreprocessor(config)
    preprocessed = preprocessor.process_source(source)

    if preprocessed.has_errors:
        logger.warning(f"Preprocessor warnings: {preprocessed.errors}")

    # Now parse the preprocessed source
    try:
        # Reset node ID counter for this parse
        _reset_node_id_counter()

        # Extract ID metadata from preprocessed source
        preprocessed_source, id_metadata = _preprocess_cobol_source(preprocessed.source)

        # Create input stream (uppercase for case-insensitivity)
        input_stream = InputStream(preprocessed_source.upper())

        # Create lexer and token stream
        lexer = Cobol85Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)

        # Create parser
        parser = Cobol85Parser(token_stream)

        # Parse the program
        tree = parser.startRule()  # type: ignore[no-untyped-call]

        # Check for syntax errors
        if parser.getNumberOfSyntaxErrors() > 0:
            error_msg = f"Parsing failed with {parser.getNumberOfSyntaxErrors()} syntax error(s)"
            logger.error(error_msg)
            raise SyntaxError(error_msg)

        # Extract comments from token stream
        comments = _extract_comments_from_token_stream(token_stream)

        # Convert ANTLR tree to ParseNode
        parse_node = _antlr_to_parse_node(tree, parser)

        # Transform to compatible format for AST builder
        program_node = _extract_program_node(parse_node)

        logger.info(
            f"Successfully parsed COBOL source with copybooks - "
            f"{len(preprocessed.copybook_usages)} copybooks found"
        )
        return program_node, comments, id_metadata, preprocessed

    except Exception as e:
        logger.error(f"Failed to parse COBOL source: {e}")
        raise SyntaxError(f"Failed to parse COBOL: {e}") from e

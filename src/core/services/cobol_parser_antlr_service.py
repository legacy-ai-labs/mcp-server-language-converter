"""COBOL parser service using ANTLR4.

This module provides COBOL parsing capabilities using ANTLR4 with the official
Cobol85 grammar from antlr/grammars-v4. The parser converts ANTLR parse trees
to our ParseNode format for compatibility with existing services.
"""

import logging
from pathlib import Path
from typing import Any

from antlr4 import CommonTokenStream, FileStream, InputStream
from antlr4.tree.Tree import TerminalNode

from src.core.models.cobol_analysis_model import Comment, CommentType, SourceLocation
from src.core.services.antlr_cobol.grammars.Cobol85Lexer import Cobol85Lexer
from src.core.services.antlr_cobol.grammars.Cobol85Parser import Cobol85Parser


logger = logging.getLogger(__name__)


class ParseNode:
    """Parse tree node compatible with PLY parser output.

    Enhanced with full-fidelity support: preserves source positions
    (line and column) for accurate source code reconstruction.
    """

    def __init__(self, node_type: str, children: list[Any] | None = None, value: Any = None):
        self.node_type = node_type
        self.children = children or []
        self.value = value
        self.line_number: int | None = None
        self.column_number: int | None = None  # Column position for full-fidelity

    def __repr__(self) -> str:
        if self.value is not None:
            return f"{self.node_type}({self.value})"
        if self.children:
            return f"{self.node_type}({len(self.children)} children)"
        return self.node_type


def _extract_value_from_children(children: list[ParseNode]) -> str | None:
    """Recursively extract string value from ParseNode children.

    This function searches through children (and their descendants) to find
    the first terminal node with a non-None string value.

    Args:
        children: List of ParseNode children to search

    Returns:
        First non-None string value found, or None if no value exists
    """
    if not children:
        return None

    for child in children:
        # Direct value on this child
        if child.value is not None and isinstance(child.value, str):
            return str(child.value)

        # Recursively search grandchildren
        if child.children:
            value = _extract_value_from_children(child.children)
            if value is not None:
                return value

    return None


def _antlr_to_parse_node(tree: Any, parser: Cobol85Parser) -> ParseNode:
    """Convert ANTLR parse tree to ParseNode format with full-fidelity support.

    Preserves both line and column numbers for accurate source reconstruction.

    Args:
        tree: ANTLR parse tree node (RuleContext or TerminalNode)
        parser: Cobol85Parser instance for accessing rule names

    Returns:
        ParseNode compatible with existing services
    """
    # Terminal node (leaf) - has token value
    if isinstance(tree, TerminalNode):
        symbol = tree.getSymbol()
        token_type = (
            parser.symbolicNames[symbol.type]
            if symbol.type < len(parser.symbolicNames)
            else "UNKNOWN"
        )
        node = ParseNode(node_type=token_type, value=symbol.text)
        node.line_number = symbol.line
        node.column_number = symbol.column  # Capture column for full-fidelity
        return node

    # Rule node (internal) - has children
    rule_name = parser.ruleNames[tree.getRuleIndex()]
    children = (
        [_antlr_to_parse_node(child, parser) for child in tree.children] if tree.children else []
    )

    # Create node with appropriate name
    node_type = rule_name.upper()

    # Special handling for some nodes to extract values
    value = None
    if rule_name in ["programName", "paragraphName", "procedureName", "dataName", "fileName"]:
        # Extract identifier value from children (recursively if needed)
        value = _extract_value_from_children(children)

    node = ParseNode(node_type=node_type, children=children, value=value)

    # Try to get line and column numbers from first token
    if hasattr(tree, "start") and tree.start:
        node.line_number = tree.start.line
        node.column_number = tree.start.column  # Capture column for full-fidelity

    return node


def _normalize_node_names(node: ParseNode) -> None:
    """Normalize ANTLR node names to match PLY parser format.

    ANTLR uses: IDENTIFICATIONDIVISION, DATADIVISION, PROCEDUREDIVISION
    PLY uses: IDENTIFICATION_DIVISION, DATA_DIVISION, PROCEDURE_DIVISION

    This function recursively updates node names for compatibility.

    Args:
        node: ParseNode to normalize (modified in place)
    """
    # Mapping of ANTLR names to PLY names
    name_map = {
        # Divisions and sections
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
        # Statement types
        "MOVESTATEMENT": "MOVE_STATEMENT",
        "PERFORMSTATEMENT": "PERFORM_STATEMENT",
        "IFSTATEMENT": "IF_STATEMENT",
        "IFELSESTATEMENT": "IF_ELSE_STATEMENT",
        "CALLSTATEMENT": "CALL_STATEMENT",
        "COMPUTESTATEMENT": "COMPUTE_STATEMENT",
        "READSTATEMENT": "READ_STATEMENT",
        "WRITESTATEMENT": "WRITE_STATEMENT",
        "OPENSTATEMENT": "OPEN_STATEMENT",
        "CLOSESTATEMENT": "CLOSE_STATEMENT",
        "DISPLAYSTATEMENT": "DISPLAY_STATEMENT",
        "ADDSTATEMENT": "ADD_STATEMENT",
        "EVALUATESTATEMENT": "EVALUATE_STATEMENT",
        "EXITSTATEMENT": "EXIT_STATEMENT",
        "STOPSTATEMENT": "STOP_STATEMENT",
    }

    # Rename current node if it matches
    if node.node_type in name_map:
        node.node_type = name_map[node.node_type]

    # Recursively normalize children
    for child in node.children:
        _normalize_node_names(child)


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

    The ANTLR parser produces: STARTRULE -> COMPILATIONUNIT -> PROGRAMUNIT
    But the AST builder expects: PROGRAM (root node)

    Args:
        parse_tree: ANTLR parse tree with STARTRULE root

    Returns:
        PROGRAMUNIT node renamed to PROGRAM with normalized node names

    Raises:
        SyntaxError: If expected structure is not found
    """
    # Navigate: STARTRULE -> COMPILATIONUNIT -> PROGRAMUNIT
    if parse_tree.node_type != "STARTRULE":
        raise SyntaxError(f"Expected STARTRULE root, got {parse_tree.node_type}")

    # Find COMPILATIONUNIT child
    compilation_unit: ParseNode | None = None
    for child in parse_tree.children:
        if isinstance(child, ParseNode) and child.node_type == "COMPILATIONUNIT":
            compilation_unit = child
            break

    if not compilation_unit:
        raise SyntaxError("No COMPILATIONUNIT found in parse tree")

    # Find PROGRAMUNIT child
    program_unit: ParseNode | None = None
    for child in compilation_unit.children:
        if isinstance(child, ParseNode) and child.node_type == "PROGRAMUNIT":
            program_unit = child
            break

    if not program_unit:
        raise SyntaxError("No PROGRAMUNIT found in COMPILATIONUNIT")

    # Rename PROGRAMUNIT to PROGRAM for compatibility with AST builder
    program_unit.node_type = "PROGRAM"

    # Normalize all node names in the tree to match PLY format
    _normalize_node_names(program_unit)

    return program_unit


def parse_cobol(source: str) -> tuple[ParseNode, list[Comment]]:
    """Parse COBOL source code and return parse tree with comments (full-fidelity).

    Args:
        source: COBOL source code as string

    Returns:
        Tuple of (ParseNode representing program structure, List of Comment objects)

    Raises:
        SyntaxError: If parsing fails
    """
    try:
        # Create input stream from source
        input_stream = InputStream(source.upper())

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
        return program_node, comments

    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise SyntaxError(f"Failed to parse COBOL: {e}") from e


def parse_cobol_file(file_path: str) -> tuple[ParseNode, list[Comment]]:
    """Parse a COBOL file and return parse tree with comments (full-fidelity).

    Args:
        file_path: Path to COBOL source file

    Returns:
        Tuple of (ParseNode representing program structure, List of Comment objects)

    Raises:
        FileNotFoundError: If file doesn't exist
        SyntaxError: If parsing fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"COBOL file not found: {file_path}")

    logger.info(f"Parsing COBOL file: {file_path}")

    try:
        # Create file input stream
        input_stream = FileStream(str(path), encoding="utf-8")

        # Preprocess: convert to uppercase (COBOL is case-insensitive)
        source = path.read_text(encoding="utf-8").upper()
        input_stream = InputStream(source)

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
        return program_node, comments

    except Exception as e:
        logger.error(f"Failed to parse file {file_path}: {e}")
        raise SyntaxError(f"Failed to parse COBOL: {e}") from e


def _reset_parser() -> None:
    """Reset parser state (for testing).

    Note: ANTLR parsers are stateless, so this is a no-op.
    Provided for compatibility with PLY parser interface.
    """
    pass

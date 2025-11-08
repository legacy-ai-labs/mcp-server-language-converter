"""COBOL parser service using PLY.

This module provides COBOL parsing capabilities using PLY (Python Lex-Yacc).
The parser handles basic COBOL constructs and produces a parse tree suitable
for AST construction.
"""

import logging
from pathlib import Path
from typing import Any, cast

from ply import lex, yacc


logger = logging.getLogger(__name__)


# ============================================================================
# Lexer (Token Definitions)
# ============================================================================

tokens = (
    # Keywords
    "IDENTIFICATION",
    "DIVISION",
    "PROGRAM_ID",
    "ENVIRONMENT",
    "DATA",
    "PROCEDURE",
    "WORKING_STORAGE",
    "LINKAGE",
    "FILE",
    "SECTION",
    "INPUT_OUTPUT",
    "FILE_CONTROL",
    "SELECT",
    "ASSIGN",
    "TO",
    "ORGANIZATION",
    "IS",
    "SEQUENTIAL",
    "ACCESS",
    "MODE",
    "FD",
    "PERFORM",
    "UNTIL",
    "END_PERFORM",
    "CALL",
    "IF",
    "ELSE",
    "END_IF",
    "EVALUATE",
    "WHEN",
    "OTHER",
    "END_EVALUATE",
    "COMPUTE",
    "MOVE",
    "READ",
    "WRITE",
    "OPEN",
    "CLOSE",
    "INPUT",
    "OUTPUT",
    "EXIT",
    "PROGRAM",
    "STOP",
    "RUN",
    "CONTINUE",
    "DISPLAY",
    "ADD",
    "SUBTRACT",
    "MULTIPLY",
    "DIVIDE",
    "VALUE",
    "ZERO",
    "SPACE",
    "USING",
    "PIC",
    "PICTURE",
    # Operators
    "LESS_THAN",
    "GREATER_THAN",
    "EQUALS",
    "NOT_EQUALS",
    "LESS_EQUAL",
    "GREATER_EQUAL",
    "PLUS",
    "MINUS",
    "MULTIPLY_OP",
    "DIVIDE_OP",
    # Literals and identifiers
    "IDENTIFIER",
    "STRING_LITERAL",
    "NUMBER",
    # Punctuation
    "DOT",
    "COMMA",
    "LPAREN",
    "RPAREN",
    "PERIOD",
    "MINUS_SIGN",
    # Special
    "NEWLINE",
    "WS",
)

# Reserved words mapping
reserved = {
    "IDENTIFICATION": "IDENTIFICATION",
    "DIVISION": "DIVISION",
    "PROGRAM-ID": "PROGRAM_ID",
    "ENVIRONMENT": "ENVIRONMENT",
    "DATA": "DATA",
    "PROCEDURE": "PROCEDURE",
    "WORKING-STORAGE": "WORKING_STORAGE",
    "LINKAGE": "LINKAGE",
    "FILE": "FILE",
    "SECTION": "SECTION",
    "INPUT-OUTPUT": "INPUT_OUTPUT",
    "FILE-CONTROL": "FILE_CONTROL",
    "SELECT": "SELECT",
    "ASSIGN": "ASSIGN",
    "TO": "TO",
    "ORGANIZATION": "ORGANIZATION",
    "IS": "IS",
    "SEQUENTIAL": "SEQUENTIAL",
    "ACCESS": "ACCESS",
    "MODE": "MODE",
    "FD": "FD",
    "PERFORM": "PERFORM",
    "UNTIL": "UNTIL",
    "END-PERFORM": "END_PERFORM",
    "CALL": "CALL",
    "IF": "IF",
    "ELSE": "ELSE",
    "END-IF": "END_IF",
    "EVALUATE": "EVALUATE",
    "WHEN": "WHEN",
    "OTHER": "OTHER",
    "END-EVALUATE": "END_EVALUATE",
    "COMPUTE": "COMPUTE",
    "MOVE": "MOVE",
    "READ": "READ",
    "WRITE": "WRITE",
    "OPEN": "OPEN",
    "CLOSE": "CLOSE",
    "INPUT": "INPUT",
    "OUTPUT": "OUTPUT",
    "EXIT": "EXIT",
    "PROGRAM": "PROGRAM",
    "STOP": "STOP",
    "RUN": "RUN",
    "CONTINUE": "CONTINUE",
    "DISPLAY": "DISPLAY",
    "ADD": "ADD",
    "SUBTRACT": "SUBTRACT",
    "MULTIPLY": "MULTIPLY",
    "DIVIDE": "DIVIDE",
    "VALUE": "VALUE",
    "ZERO": "ZERO",
    "ZEROS": "ZERO",
    "SPACES": "SPACE",
    "SPACE": "SPACE",
    "USING": "USING",
    "PIC": "PIC",
    "PICTURE": "PIC",
}

# Token regex patterns
t_LESS_THAN = r"<"
t_GREATER_THAN = r">"
t_EQUALS = r"="
t_NOT_EQUALS = r"<>"
t_LESS_EQUAL = r"<="
t_GREATER_EQUAL = r">="
t_PLUS = r"\+"
t_MINUS = r"-"
t_MULTIPLY_OP = r"\*"
t_DIVIDE_OP = r"/"
t_DOT = r"\."
t_COMMA = r","
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_PERIOD = r"\."


def t_IDENTIFIER(t: lex.LexToken) -> lex.LexToken:
    r"[A-Z][A-Z0-9\-]*"
    # Check if it's a reserved word
    t.type = reserved.get(t.value.upper(), "IDENTIFIER")
    return t


def t_STRING_LITERAL(t: lex.LexToken) -> lex.LexToken:
    r"'[^']*'"
    t.value = t.value[1:-1]  # Remove quotes
    return t


def t_NUMBER(t: lex.LexToken) -> lex.LexToken:
    r"\d+(\.\d+)?"
    t.value = float(t.value) if "." in t.value else int(t.value)
    return t


def t_NEWLINE(t: lex.LexToken) -> lex.LexToken:
    r"\n+"
    t.lexer.lineno += len(t.value)
    return t


def t_WS(t: lex.LexToken) -> None:
    r"[ \t]+"
    del t  # Ignore whitespace


def t_COMMENT(t: lex.LexToken) -> None:
    r"\*.*"
    del t  # Ignore comments


def t_error(t: lex.LexToken) -> None:
    logger.warning(f"Illegal character '{t.value[0]}' at line {t.lineno}")
    t.lexer.skip(1)


# ============================================================================
# Parser (Grammar Rules)
# ============================================================================


# Parse tree node classes
class ParseNode:
    """Base class for parse tree nodes."""

    def __init__(self, node_type: str, children: list[Any] | None = None, value: Any = None):
        self.node_type = node_type
        self.children = children or []
        self.value = value
        self.line_number: int | None = None

    def __repr__(self) -> str:
        if self.value is not None:
            return f"{self.node_type}({self.value})"
        if self.children:
            return f"{self.node_type}({len(self.children)} children)"
        return self.node_type


def p_program(p: yacc.YaccProduction) -> None:
    """program : identification_division environment_division data_division procedure_division"""
    p[0] = ParseNode(
        "PROGRAM",
        children=[p[1], p[2], p[3], p[4]],
    )


def p_identification_division(p: yacc.YaccProduction) -> None:
    """identification_division : IDENTIFICATION DIVISION DOT program_id_clause"""
    p[0] = ParseNode("IDENTIFICATION_DIVISION", children=[p[4]] if len(p) > 4 else [])


def p_program_id_clause(p: yacc.YaccProduction) -> None:
    """program_id_clause : PROGRAM_ID IDENTIFIER DOT"""
    p[0] = ParseNode("PROGRAM_ID", value=p[2])


def p_environment_division(p: yacc.YaccProduction) -> None:
    """environment_division : ENVIRONMENT DIVISION DOT input_output_section"""
    p[0] = ParseNode("ENVIRONMENT_DIVISION", children=[p[4]] if len(p) > 4 else [])


def p_input_output_section(p: yacc.YaccProduction) -> None:
    """input_output_section : INPUT_OUTPUT SECTION DOT FILE_CONTROL DOT file_control_entry"""
    p[0] = ParseNode("INPUT_OUTPUT_SECTION", children=[p[6]] if len(p) > 6 else [])


def p_file_control_entry(p: yacc.YaccProduction) -> None:
    """file_control_entry : SELECT IDENTIFIER ASSIGN TO STRING_LITERAL file_org_clause DOT"""
    p[0] = ParseNode(
        "FILE_CONTROL_ENTRY",
        children=[
            ParseNode("FILE_NAME", value=p[2]),
            ParseNode("FILE_ASSIGN", value=p[4]),
            p[5] if len(p) > 5 else ParseNode("EMPTY"),
        ],
    )


def p_file_org_clause(p: yacc.YaccProduction) -> None:
    """file_org_clause : ORGANIZATION IS SEQUENTIAL ACCESS MODE IS SEQUENTIAL DOT"""
    p[0] = ParseNode("FILE_ORGANIZATION", value="SEQUENTIAL")


def p_data_division(p: yacc.YaccProduction) -> None:
    """data_division : DATA DIVISION DOT data_sections"""
    p[0] = ParseNode("DATA_DIVISION", children=[p[4]] if len(p) > 4 else [])


def p_data_sections(p: yacc.YaccProduction) -> None:
    """data_sections : file_section working_storage_section
    | file_section
    | working_storage_section
    | linkage_section
    | file_section linkage_section
    """
    if len(p) == 3:
        p[0] = ParseNode("DATA_SECTIONS", children=[p[1], p[2]])
    else:
        p[0] = ParseNode("DATA_SECTIONS", children=[p[1]])


def p_file_section(p: yacc.YaccProduction) -> None:
    """file_section : FILE SECTION DOT fd_entry_list"""
    p[0] = ParseNode("FILE_SECTION", children=[p[4]] if len(p) > 4 else [])


def p_fd_entry_list(p: yacc.YaccProduction) -> None:
    """fd_entry_list : fd_entry
    | fd_entry fd_entry_list
    """
    if len(p) == 2:
        p[0] = ParseNode("FD_ENTRY_LIST", children=[p[1]])
    else:
        p[0] = ParseNode("FD_ENTRY_LIST", children=[p[1], *p[2].children])


def p_fd_entry(p: yacc.YaccProduction) -> None:
    """fd_entry : FD IDENTIFIER DOT record_definition_list"""
    p[0] = ParseNode("FD_ENTRY", children=[ParseNode("FD_NAME", value=p[2]), p[4]])


def p_record_definition_list(p: yacc.YaccProduction) -> None:
    """record_definition_list : record_definition
    | record_definition record_definition_list
    """
    if len(p) == 2:
        p[0] = ParseNode("RECORD_DEFINITION_LIST", children=[p[1]])
    else:
        p[0] = ParseNode("RECORD_DEFINITION_LIST", children=[p[1], *p[2].children])


def p_record_definition(p: yacc.YaccProduction) -> None:
    """record_definition : level_number IDENTIFIER PIC pic_clause DOT"""
    p[0] = ParseNode(
        "RECORD_DEFINITION",
        children=[
            ParseNode("LEVEL", value=p[1]),
            ParseNode("FIELD_NAME", value=p[2]),
            p[4],
        ],
    )


def p_level_number(p: yacc.YaccProduction) -> None:
    """level_number : NUMBER"""
    p[0] = int(p[1])


def p_working_storage_section(p: yacc.YaccProduction) -> None:
    """working_storage_section : WORKING_STORAGE SECTION DOT ws_definitions"""
    p[0] = ParseNode("WORKING_STORAGE_SECTION", children=[p[3]] if len(p) > 3 else [])


def p_linkage_section(p: yacc.YaccProduction) -> None:
    """linkage_section : LINKAGE SECTION DOT linkage_definition_list"""
    p[0] = ParseNode("LINKAGE_SECTION", children=[p[4]] if len(p) > 4 else [])


def p_linkage_definition_list(p: yacc.YaccProduction) -> None:
    """linkage_definition_list : linkage_definition
    | linkage_definition linkage_definition_list
    """
    if len(p) == 2:
        p[0] = ParseNode("LINKAGE_DEFINITION_LIST", children=[p[1]])
    else:
        p[0] = ParseNode("LINKAGE_DEFINITION_LIST", children=[p[1], *p[2].children])


def p_ws_definitions(p: yacc.YaccProduction) -> None:
    """ws_definitions : ws_definition ws_definitions
    | ws_definition
    """
    if len(p) == 3:
        p[0] = ParseNode("WS_DEFINITIONS", children=[p[1], *p[2].children])
    else:
        p[0] = ParseNode("WS_DEFINITIONS", children=[p[1]])


def p_ws_definition(p: yacc.YaccProduction) -> None:
    """ws_definition : level_number IDENTIFIER PIC pic_clause value_clause DOT
    | level_number IDENTIFIER PIC pic_clause DOT
    | level_number IDENTIFIER value_clause DOT
    | level_number IDENTIFIER DOT
    """
    children = [
        ParseNode("LEVEL", value=p[1]),
        ParseNode("VARIABLE_NAME", value=p[2]),
    ]
    if len(p) > 4 and p[3] == "PIC":
        children.append(p[4])  # PIC clause
        if len(p) > 5 and p[5] != ".":
            children.append(p[5])  # VALUE clause
    elif len(p) > 4 and p[3] != ".":
        children.append(p[3])  # VALUE clause without PIC
    p[0] = ParseNode("WS_DEFINITION", children=children)


def p_linkage_definition(p: yacc.YaccProduction) -> None:
    """linkage_definition : level_number IDENTIFIER PIC pic_clause DOT"""
    p[0] = ParseNode(
        "LINKAGE_DEFINITION",
        children=[
            ParseNode("LEVEL", value=p[1]),
            ParseNode("PARAMETER_NAME", value=p[2]),
            p[4],
        ],
    )


def p_pic_clause(p: yacc.YaccProduction) -> None:
    """pic_clause : PIC STRING_LITERAL
    | PIC IDENTIFIER
    """
    p[0] = ParseNode("PIC_CLAUSE", value=p[2])


def p_value_clause(p: yacc.YaccProduction) -> None:
    """value_clause : VALUE STRING_LITERAL
    | VALUE NUMBER
    | VALUE ZERO
    | VALUE SPACE
    """
    if p[2] == "ZERO":
        p[0] = ParseNode("VALUE_CLAUSE", value=0)
    elif p[2] == "SPACE" or p[2] == "SPACES":
        p[0] = ParseNode("VALUE_CLAUSE", value=" ")
    else:
        p[0] = ParseNode("VALUE_CLAUSE", value=p[2])


def p_procedure_division(p: yacc.YaccProduction) -> None:
    """procedure_division : PROCEDURE DIVISION DOT procedure_body
    | PROCEDURE DIVISION USING identifier_list DOT procedure_body
    """
    if len(p) > 5:
        p[0] = ParseNode("PROCEDURE_DIVISION", children=[p[4], p[6]])
    else:
        p[0] = ParseNode("PROCEDURE_DIVISION", children=[p[4]])


def p_identifier_list(p: yacc.YaccProduction) -> None:
    """identifier_list : IDENTIFIER
    | IDENTIFIER identifier_list
    """
    if len(p) == 2:
        p[0] = ParseNode("IDENTIFIER_LIST", children=[ParseNode("IDENTIFIER", value=p[1])])
    else:
        p[0] = ParseNode(
            "IDENTIFIER_LIST", children=[ParseNode("IDENTIFIER", value=p[1]), *p[2].children]
        )


def p_procedure_body(p: yacc.YaccProduction) -> None:
    """procedure_body : paragraph procedure_body
    | paragraph
    """
    if len(p) == 3:
        p[0] = ParseNode("PROCEDURE_BODY", children=[p[1], *p[2].children])
    else:
        p[0] = ParseNode("PROCEDURE_BODY", children=[p[1]])


def p_paragraph(p: yacc.YaccProduction) -> None:
    """paragraph : paragraph_name statements DOT"""
    p[0] = ParseNode("PARAGRAPH", children=[p[1], p[2]])


def p_paragraph_name(p: yacc.YaccProduction) -> None:
    """paragraph_name : IDENTIFIER DOT"""
    p[0] = ParseNode("PARAGRAPH_NAME", value=p[1])


def p_statements(p: yacc.YaccProduction) -> None:
    """statements : statement statements
    | statement
    """
    if len(p) == 3:
        p[0] = ParseNode("STATEMENTS", children=[p[1], *p[2].children])
    else:
        p[0] = ParseNode("STATEMENTS", children=[p[1]])


def p_statement(p: yacc.YaccProduction) -> None:
    """statement : perform_statement
    | if_statement
    | call_statement
    | compute_statement
    | move_statement
    | read_statement
    | write_statement
    | open_statement
    | close_statement
    | display_statement
    | add_statement
    | evaluate_statement
    | exit_statement
    | stop_statement
    """
    p[0] = p[1]


def p_perform_statement(p: yacc.YaccProduction) -> None:
    """perform_statement : PERFORM IDENTIFIER DOT
    | PERFORM IDENTIFIER UNTIL condition DOT statements END_PERFORM DOT
    """
    if len(p) == 4:
        p[0] = ParseNode("PERFORM_STATEMENT", children=[ParseNode("PARAGRAPH_NAME", value=p[2])])
    else:
        p[0] = ParseNode(
            "PERFORM_UNTIL_STATEMENT",
            children=[
                ParseNode("PARAGRAPH_NAME", value=p[2]),
                p[4],  # condition
                p[6],  # statements
            ],
        )


def p_if_statement(p: yacc.YaccProduction) -> None:
    """if_statement : IF condition DOT statements END_IF DOT
    | IF condition DOT statements ELSE DOT statements END_IF DOT
    """
    if len(p) == 6:
        p[0] = ParseNode("IF_STATEMENT", children=[p[2], p[4]])  # condition, statements
    else:
        p[0] = ParseNode("IF_ELSE_STATEMENT", children=[p[2], p[4], p[7]])  # condition, then, else


def p_condition(p: yacc.YaccProduction) -> None:
    """condition : IDENTIFIER LESS_THAN NUMBER
    | IDENTIFIER GREATER_THAN NUMBER
    | IDENTIFIER EQUALS STRING_LITERAL
    | IDENTIFIER EQUALS IDENTIFIER
    | IDENTIFIER GREATER_EQUAL NUMBER
    | IDENTIFIER LESS_EQUAL NUMBER
    """
    p[0] = ParseNode(
        "CONDITION",
        children=[
            ParseNode("LEFT", value=p[1]),
            ParseNode("OPERATOR", value=p[2]),
            ParseNode("RIGHT", value=p[3]),
        ],
    )


def p_call_statement(p: yacc.YaccProduction) -> None:
    """call_statement : CALL STRING_LITERAL USING identifier_list DOT"""
    p[0] = ParseNode(
        "CALL_STATEMENT",
        children=[
            ParseNode("PROGRAM_NAME", value=p[2]),
            p[4] if len(p) > 4 else ParseNode("EMPTY"),
        ],
    )


def p_compute_statement(p: yacc.YaccProduction) -> None:
    """compute_statement : COMPUTE IDENTIFIER EQUALS expression DOT"""
    p[0] = ParseNode(
        "COMPUTE_STATEMENT",
        children=[
            ParseNode("TARGET", value=p[2]),
            p[4] if len(p) > 4 else ParseNode("EMPTY"),
        ],
    )


def p_expression(p: yacc.YaccProduction) -> None:
    """expression : IDENTIFIER
    | NUMBER
    | IDENTIFIER PLUS NUMBER
    | IDENTIFIER MINUS NUMBER
    | IDENTIFIER MULTIPLY_OP NUMBER
    | IDENTIFIER DIVIDE_OP NUMBER
    """
    if len(p) == 2:
        p[0] = ParseNode("EXPRESSION", value=p[1])
    else:
        p[0] = ParseNode(
            "EXPRESSION",
            children=[
                ParseNode("LEFT", value=p[1]),
                ParseNode("OPERATOR", value=p[2]),
                ParseNode("RIGHT", value=p[3]),
            ],
        )


def p_move_statement(p: yacc.YaccProduction) -> None:
    """move_statement : MOVE IDENTIFIER TO IDENTIFIER DOT"""
    p[0] = ParseNode(
        "MOVE_STATEMENT",
        children=[
            ParseNode("SOURCE", value=p[2]),
            ParseNode("TARGET", value=p[4]),
        ],
    )


def p_read_statement(p: yacc.YaccProduction) -> None:
    """read_statement : READ IDENTIFIER DOT"""
    p[0] = ParseNode("READ_STATEMENT", children=[ParseNode("FILE_NAME", value=p[2])])


def p_write_statement(p: yacc.YaccProduction) -> None:
    """write_statement : WRITE IDENTIFIER DOT"""
    p[0] = ParseNode("WRITE_STATEMENT", children=[ParseNode("FILE_NAME", value=p[2])])


def p_open_statement(p: yacc.YaccProduction) -> None:
    """open_statement : OPEN INPUT IDENTIFIER DOT
    | OPEN OUTPUT IDENTIFIER DOT
    """
    p[0] = ParseNode("OPEN_STATEMENT", children=[ParseNode("FILE_NAME", value=p[3])])


def p_close_statement(p: yacc.YaccProduction) -> None:
    """close_statement : CLOSE IDENTIFIER DOT"""
    p[0] = ParseNode("CLOSE_STATEMENT", children=[ParseNode("FILE_NAME", value=p[2])])


def p_display_statement(p: yacc.YaccProduction) -> None:
    """display_statement : DISPLAY STRING_LITERAL DOT"""
    p[0] = ParseNode("DISPLAY_STATEMENT", value=p[2])


def p_add_statement(p: yacc.YaccProduction) -> None:
    """add_statement : ADD NUMBER TO IDENTIFIER DOT"""
    p[0] = ParseNode(
        "ADD_STATEMENT",
        children=[
            ParseNode("VALUE", value=p[2]),
            ParseNode("TARGET", value=p[4]),
        ],
    )


def p_evaluate_statement(p: yacc.YaccProduction) -> None:
    """evaluate_statement : EVALUATE IDENTIFIER when_clauses OTHER DOT statements END_EVALUATE DOT"""
    p[0] = ParseNode(
        "EVALUATE_STATEMENT",
        children=[
            ParseNode("EXPRESSION", value=p[2]),
            p[3],  # when_clauses
            p[5],  # statements (OTHER case)
        ],
    )


def p_when_clauses(p: yacc.YaccProduction) -> None:
    """when_clauses : when_clause when_clauses
    | when_clause
    """
    if len(p) == 3:
        p[0] = ParseNode("WHEN_CLAUSES", children=[p[1], *p[2].children])
    else:
        p[0] = ParseNode("WHEN_CLAUSES", children=[p[1]])


def p_when_clause(p: yacc.YaccProduction) -> None:
    """when_clause : WHEN STRING_LITERAL DOT statements"""
    p[0] = ParseNode("WHEN_CLAUSE", children=[ParseNode("VALUE", value=p[2]), p[4]])


def p_exit_statement(p: yacc.YaccProduction) -> None:
    """exit_statement : EXIT PROGRAM DOT"""
    p[0] = ParseNode("EXIT_STATEMENT")


def p_stop_statement(p: yacc.YaccProduction) -> None:
    """stop_statement : STOP RUN DOT"""
    p[0] = ParseNode("STOP_STATEMENT")


def p_error(p: yacc.YaccProduction) -> None:
    if p:
        logger.error(f"Syntax error at '{p.value}' on line {p.lineno}")
    else:
        logger.error("Syntax error at EOF")


# ============================================================================
# Parser Instance
# ============================================================================

_lexer: lex.Lexer | None = None
_parser: yacc.LRParser | None = None


def get_lexer() -> lex.Lexer:
    """Get or create the lexer instance."""
    global _lexer  # noqa: PLW0603
    if _lexer is None:
        _lexer = lex.lex()
    return _lexer


def get_parser() -> yacc.LRParser:
    """Get or create the parser instance."""
    global _parser  # noqa: PLW0603
    if _parser is None:
        _parser = yacc.yacc(debug=False, write_tables=False)
    return _parser


# ============================================================================
# Public API
# ============================================================================


def parse_cobol(source_code: str) -> ParseNode:
    """Parse COBOL source code into a parse tree.

    Args:
        source_code: COBOL source code as string

    Returns:
        ParseNode representing the root of the parse tree

    Raises:
        SyntaxError: If the COBOL code cannot be parsed
    """
    lexer = get_lexer()
    parser = get_parser()

    # Normalize line endings and handle COBOL fixed format (columns 7-72)
    # For now, we'll handle free format
    normalized_source = source_code.replace("\r\n", "\n").replace("\r", "\n")

    try:
        result = parser.parse(normalized_source, lexer=lexer, debug=False)
        if result is None:
            raise SyntaxError("Parser returned None - check syntax")
        # PLY parser returns Any, but we know it's ParseNode based on our grammar
        return cast(ParseNode, result)
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise SyntaxError(f"Failed to parse COBOL: {e}") from e


def parse_cobol_file(file_path: str) -> ParseNode:
    """Parse COBOL file into a parse tree.

    Args:
        file_path: Path to COBOL source file

    Returns:
        ParseNode representing the root of the parse tree

    Raises:
        FileNotFoundError: If file doesn't exist
        SyntaxError: If the COBOL code cannot be parsed
    """
    try:
        source_code = Path(file_path).read_text(encoding="utf-8")
        return parse_cobol(source_code)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise

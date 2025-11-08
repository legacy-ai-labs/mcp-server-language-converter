"""Tests for the COBOL AST builder."""

from src.core.models.cobol_analysis_model import DivisionType, StatementType
from src.core.services.ast_builder_service import build_ast
from src.core.services.cobol_parser_service import ParseNode


def _create_sample_program_parse_tree() -> ParseNode:
    program_id = ParseNode("PROGRAM_ID", value="SAMPLE")
    ident_division = ParseNode("IDENTIFICATION_DIVISION", children=[program_id])

    file_entry = ParseNode(
        "FILE_CONTROL_ENTRY",
        children=[
            ParseNode("FILE_NAME", value="INPUTFILE"),
            ParseNode("FILE_ASSIGN", value="DISK"),
            ParseNode("FILE_ORGANIZATION", value="SEQUENTIAL"),
        ],
    )
    input_output_section = ParseNode("INPUT_OUTPUT_SECTION", children=[file_entry])
    environment_division = ParseNode("ENVIRONMENT_DIVISION", children=[input_output_section])

    ws_definition = ParseNode(
        "WS_DEFINITION",
        children=[
            ParseNode("LEVEL", value=1),
            ParseNode("VARIABLE_NAME", value="BALANCE"),
            ParseNode("PIC_CLAUSE", value="9"),
            ParseNode("VALUE_CLAUSE", value=0),
        ],
    )
    ws_definitions = ParseNode("WS_DEFINITIONS", children=[ws_definition])
    working_storage_section = ParseNode("WORKING_STORAGE_SECTION", children=[ws_definitions])
    data_division = ParseNode("DATA_DIVISION", children=[working_storage_section])

    condition = ParseNode(
        "CONDITION",
        children=[
            ParseNode("LEFT", value="BALANCE"),
            ParseNode("OPERATOR", value="<"),
            ParseNode("RIGHT", value=0),
        ],
    )
    display_statement = ParseNode("DISPLAY_STATEMENT", value="NEGATIVE")
    inner_statements = ParseNode("STATEMENTS", children=[display_statement])
    if_statement = ParseNode("IF_STATEMENT", children=[condition, inner_statements])
    statements = ParseNode("STATEMENTS", children=[if_statement])
    paragraph = ParseNode(
        "PARAGRAPH", children=[ParseNode("PARAGRAPH_NAME", value="MAIN"), statements]
    )
    procedure_body = ParseNode("PROCEDURE_BODY", children=[paragraph])
    procedure_division = ParseNode("PROCEDURE_DIVISION", children=[procedure_body])

    return ParseNode(
        "PROGRAM",
        children=[ident_division, environment_division, data_division, procedure_division],
    )


def test_build_ast_creates_program_structure() -> None:
    parse_tree = _create_sample_program_parse_tree()

    program = build_ast(parse_tree)

    assert program.program_name == "SAMPLE"
    assert {division.division_type for division in program.divisions} == {
        DivisionType.IDENTIFICATION,
        DivisionType.ENVIRONMENT,
        DivisionType.DATA,
        DivisionType.PROCEDURE,
    }


def test_build_ast_builds_procedure_statements() -> None:
    parse_tree = _create_sample_program_parse_tree()

    program = build_ast(parse_tree)
    procedure_division = next(
        division
        for division in program.divisions
        if division.division_type == DivisionType.PROCEDURE
    )
    procedure_section = procedure_division.sections[0]
    paragraph = procedure_section.paragraphs[0]
    statement = paragraph.statements[0]

    assert statement.statement_type == StatementType.IF
    assert statement.attributes["condition"].operator == "<"
    then_statements = statement.attributes["then_statements"]
    assert len(then_statements) == 1
    assert then_statements[0].statement_type == StatementType.DISPLAY

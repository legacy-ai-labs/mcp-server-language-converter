"""Build Abstract Syntax Trees (AST) from COBOL parse trees.

The COBOL parser (see ``cobol_parser_service.py``) produces a generic parse tree built
from :class:`ParseNode`.  This module converts that intermediate representation
into the strongly typed AST models defined in ``src/core/models/cobol_analysis_model.py``.

Only a subset of the full COBOL language is currently supported by the parser,
so the builder focuses on the constructs described in
``docs/cobol/phase1/COBOL_PHASE1_DETAILED.md`` (Step 3 deliverables).  The
builder is intentionally defensive: it tolerates unknown parse nodes, logs them
for later analysis, and keeps the resulting AST structurally consistent.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

from src.core.models.cobol_analysis_model import (
    DivisionNode,
    DivisionType,
    ExpressionNode,
    LiteralNode,
    ParagraphNode,
    ProgramNode,
    SectionNode,
    StatementNode,
    StatementType,
    VariableNode,
)
from src.core.services.cobol_parser_service import ParseNode


logger = logging.getLogger(__name__)


class ASTBuilderError(ValueError):
    """Raised when the AST cannot be constructed from the provided parse tree."""


def build_ast(parsed_cobol: Any) -> ProgramNode:
    """Build an AST program node from the COBOL parse tree.

    Args:
        parsed_cobol: Root node returned by ``parse_cobol``.

    Returns:
        ProgramNode representing the COBOL program.

    Raises:
        ASTBuilderError: If the parse tree is invalid or does not represent a program.
    """
    if not isinstance(parsed_cobol, ParseNode):
        raise ASTBuilderError("Parsed COBOL must be a ParseNode instance.")

    if parsed_cobol.node_type != "PROGRAM":
        raise ASTBuilderError(f"Expected root node type 'PROGRAM', got '{parsed_cobol.node_type}'.")

    program_name = _extract_program_name(parsed_cobol) or "UNKNOWN"
    program_node = ProgramNode(program_name=program_name)

    divisions: list[DivisionNode] = []
    for child in parsed_cobol.children:
        division = _build_division(child)
        if division:
            divisions.append(division)

    program_node.divisions = divisions
    program_node.children = list(divisions)
    return program_node


# ============================================================================
# Division builders
# ============================================================================


def _build_division(node: ParseNode) -> DivisionNode | None:
    division_type = _parse_division_type(node.node_type)
    if division_type is None:
        logger.debug("Ignoring unsupported division node '%s'.", node.node_type)
        return None

    division = DivisionNode(division_type=division_type)
    sections = _build_sections_for_division(division_type, node)

    division.sections = sections
    division.children = list(sections)
    return division


def _parse_division_type(node_type: str) -> DivisionType | None:
    mapping = {
        "IDENTIFICATION_DIVISION": DivisionType.IDENTIFICATION,
        "ENVIRONMENT_DIVISION": DivisionType.ENVIRONMENT,
        "DATA_DIVISION": DivisionType.DATA,
        "PROCEDURE_DIVISION": DivisionType.PROCEDURE,
    }
    return mapping.get(node_type)


def _build_sections_for_division(division_type: DivisionType, node: ParseNode) -> list[SectionNode]:
    if division_type == DivisionType.IDENTIFICATION:
        return [_build_identification_section(node)]
    if division_type == DivisionType.ENVIRONMENT:
        return _build_environment_sections(node)
    if division_type == DivisionType.DATA:
        return _build_data_sections(node)
    if division_type == DivisionType.PROCEDURE:
        return _build_procedure_sections(node)
    return []


def _build_identification_section(node: ParseNode) -> SectionNode:
    program_id = _find_child_value(node, "PROGRAM_ID")
    section = SectionNode(section_name="PROGRAM-ID")
    if program_id:
        paragraph = ParagraphNode(paragraph_name="PROGRAM-ID")
        paragraph_statements = [
            StatementNode(
                statement_type=StatementType.DISPLAY,
                attributes={"program_id": program_id},
            )
        ]
        paragraph.statements = paragraph_statements
        paragraph.children = list(paragraph_statements)
        section.paragraphs = [paragraph]
        section.children = [paragraph]
    return section


def _build_environment_sections(node: ParseNode) -> list[SectionNode]:
    sections: list[SectionNode] = []
    for entry in _walk_nodes(node, {"INPUT_OUTPUT_SECTION"}):
        section = SectionNode(section_name="INPUT-OUTPUT")
        file_entries = []
        for child in _walk_nodes(entry, {"FILE_CONTROL_ENTRY"}):
            file_entries.append(
                StatementNode(
                    statement_type=StatementType.OPEN,
                    attributes={
                        "file_name": _find_child_value(child, "FILE_NAME"),
                        "assignment": _find_child_value(child, "FILE_ASSIGN"),
                        "organization": _find_child_value(child, "FILE_ORGANIZATION"),
                    },
                )
            )
        section.paragraphs = [
            ParagraphNode(
                paragraph_name="FILE-CONTROL", statements=file_entries, children=list(file_entries)
            )
        ]
        section.children = list(section.paragraphs)
        sections.append(section)
    return sections


def _build_data_sections(node: ParseNode) -> list[SectionNode]:
    sections: list[SectionNode] = []
    for section_node in _walk_nodes(
        node,
        {
            "FILE_SECTION",
            "WORKING_STORAGE_SECTION",
            "LINKAGE_SECTION",
        },
    ):
        section = SectionNode(
            section_name=section_node.node_type.replace("_SECTION", "").replace("_", "-")
        )
        paragraphs: list[ParagraphNode] = []

        for definition_list in section_node.children:
            if not isinstance(definition_list, ParseNode):
                continue
            for definition in definition_list.children:
                if not isinstance(definition, ParseNode):
                    continue
                paragraph = ParagraphNode(
                    paragraph_name=_find_child_value(definition, "VARIABLE_NAME")
                    or _find_child_value(definition, "FIELD_NAME")
                    or _find_child_value(definition, "PARAMETER_NAME")
                    or _find_child_value(definition, "FD_NAME")
                    or "ENTRY",
                )

                statements: list[StatementNode] = []
                pic_clause = _find_child_value(definition, "PIC_CLAUSE")
                value_clause = _find_child_value(definition, "VALUE_CLAUSE")

                if pic_clause is not None:
                    statements.append(
                        StatementNode(
                            statement_type=StatementType.MOVE,
                            attributes={"pic": pic_clause},
                        )
                    )
                if value_clause is not None:
                    literal = _create_literal(value_clause)
                    statements.append(
                        StatementNode(
                            statement_type=StatementType.MOVE,
                            attributes={"value": literal},
                        )
                    )

                if statements:
                    paragraph.statements = statements
                    paragraph.children = list(statements)
                    paragraphs.append(paragraph)

        if paragraphs:
            section.paragraphs = paragraphs
            section.children = list(paragraphs)
            sections.append(section)

    return sections


def _build_procedure_sections(node: ParseNode) -> list[SectionNode]:
    section = SectionNode(section_name="PROCEDURE")
    paragraphs = _extract_paragraphs(node)
    section.paragraphs = paragraphs
    section.children = list(paragraphs)
    return [section]


# ============================================================================
# Paragraphs and statements
# ============================================================================


def _extract_paragraphs(node: ParseNode) -> list[ParagraphNode]:
    paragraphs: list[ParagraphNode] = []
    for candidate in _walk_nodes(node, {"PARAGRAPH"}):
        paragraph_name = _find_child_value(candidate, "PARAGRAPH_NAME") or "PARAGRAPH"
        statements_node = _find_child_node(candidate, "STATEMENTS")
        statements = _build_statements(statements_node) if statements_node else []
        paragraph = ParagraphNode(paragraph_name=paragraph_name, statements=statements)
        paragraph.children = list(statements)
        paragraphs.append(paragraph)
    return paragraphs


def _build_statements(node: ParseNode | None) -> list[StatementNode]:
    if node is None:
        return []
    statements: list[StatementNode] = []
    for child in node.children:
        if isinstance(child, ParseNode):
            statement = _build_statement(child)
            if statement:
                statements.append(statement)
    return statements


def _build_statement(node: ParseNode) -> StatementNode | None:
    def _build_read_statement(parse_node: ParseNode) -> StatementNode:
        return StatementNode(
            statement_type=StatementType.READ,
            attributes={"file_name": _find_child_value(parse_node, "FILE_NAME")},
        )

    def _build_write_statement(parse_node: ParseNode) -> StatementNode:
        return StatementNode(
            statement_type=StatementType.WRITE,
            attributes={"file_name": _find_child_value(parse_node, "FILE_NAME")},
        )

    def _build_open_statement(parse_node: ParseNode) -> StatementNode:
        return StatementNode(
            statement_type=StatementType.OPEN,
            attributes={"file_name": _find_child_value(parse_node, "FILE_NAME")},
        )

    def _build_close_statement(parse_node: ParseNode) -> StatementNode:
        return StatementNode(
            statement_type=StatementType.CLOSE,
            attributes={"file_name": _find_child_value(parse_node, "FILE_NAME")},
        )

    def _build_exit_statement(_: ParseNode) -> StatementNode:
        return StatementNode(statement_type=StatementType.EXIT)

    def _build_stop_statement(_: ParseNode) -> StatementNode:
        return StatementNode(statement_type=StatementType.STOP)

    builder_map: dict[str, Callable[[ParseNode], StatementNode | None]] = {
        "PERFORM_STATEMENT": _build_perform_statement,
        "PERFORM_UNTIL_STATEMENT": _build_perform_until_statement,
        "IF_STATEMENT": _build_if_statement,
        "IF_ELSE_STATEMENT": _build_if_else_statement,
        "CALL_STATEMENT": _build_call_statement,
        "COMPUTE_STATEMENT": _build_compute_statement,
        "MOVE_STATEMENT": _build_move_statement,
        "READ_STATEMENT": _build_read_statement,
        "WRITE_STATEMENT": _build_write_statement,
        "OPEN_STATEMENT": _build_open_statement,
        "CLOSE_STATEMENT": _build_close_statement,
        "DISPLAY_STATEMENT": lambda n: StatementNode(
            statement_type=StatementType.DISPLAY,
            attributes={"message": _create_literal(n.value)},
        ),
        "ADD_STATEMENT": _build_add_statement,
        "EVALUATE_STATEMENT": _build_evaluate_statement,
        "EXIT_STATEMENT": _build_exit_statement,
        "STOP_STATEMENT": _build_stop_statement,
    }

    builder = builder_map.get(node.node_type)
    if builder is None:
        logger.debug("Unsupported statement node encountered: %s", node.node_type)
        return None

    statement = builder(node)
    if statement is None:
        return None

    # Propagate child nodes for tree traversal consumers.
    child_nodes: list[StatementNode | ExpressionNode | VariableNode | LiteralNode] = []
    if "condition" in statement.attributes and isinstance(
        statement.attributes["condition"], ExpressionNode
    ):
        child_nodes.append(statement.attributes["condition"])
    if "statements" in statement.attributes and isinstance(
        statement.attributes["statements"], list
    ):
        child_nodes.extend(statement.attributes["statements"])
    if "then_statements" in statement.attributes and isinstance(
        statement.attributes["then_statements"], list
    ):
        child_nodes.extend(statement.attributes["then_statements"])
    if "else_statements" in statement.attributes and isinstance(
        statement.attributes["else_statements"], list
    ):
        child_nodes.extend(statement.attributes["else_statements"])

    statement.children = [
        node for node in child_nodes if isinstance(node, StatementNode | ExpressionNode)
    ]
    return statement


def _build_perform_statement(node: ParseNode) -> StatementNode:
    return StatementNode(
        statement_type=StatementType.PERFORM,
        attributes={"target_paragraph": _find_child_value(node, "PARAGRAPH_NAME")},
    )


def _build_perform_until_statement(node: ParseNode) -> StatementNode:
    condition_node = _find_child_node(node, "CONDITION")
    loop_statements_node = _find_child_node(node, "STATEMENTS")
    return StatementNode(
        statement_type=StatementType.PERFORM,
        attributes={
            "target_paragraph": _find_child_value(node, "PARAGRAPH_NAME"),
            "condition": _build_expression(condition_node),
            "statements": _build_statements(loop_statements_node),
            "is_until": True,
        },
    )


def _build_if_statement(node: ParseNode) -> StatementNode:
    condition = _build_expression(_find_child_node(node, "CONDITION"))
    then_statements = _build_statements(_find_child_node(node, "STATEMENTS"))
    return StatementNode(
        statement_type=StatementType.IF,
        attributes={
            "condition": condition,
            "then_statements": then_statements,
        },
    )


def _build_if_else_statement(node: ParseNode) -> StatementNode:
    condition = _build_expression(_find_child_node(node, "CONDITION"))
    then_statements = _build_statements(_find_child_node(node, "STATEMENTS"))
    else_statements = _build_statements(_find_child_node(node, "STATEMENTS", occurrence=1))
    return StatementNode(
        statement_type=StatementType.IF,
        attributes={
            "condition": condition,
            "then_statements": then_statements,
            "else_statements": else_statements,
        },
    )


def _build_call_statement(node: ParseNode) -> StatementNode:
    program_name = _find_child_value(node, "PROGRAM_NAME")
    identifiers = _walk_nodes(node, {"IDENTIFIER_LIST"})
    parameters: list[str] = []
    for identifier_list in identifiers:
        for identifier in identifier_list.children:
            if (
                isinstance(identifier, ParseNode)
                and identifier.node_type == "IDENTIFIER"
                and isinstance(identifier.value, str)
            ):
                parameters.append(identifier.value)
    return StatementNode(
        statement_type=StatementType.CALL,
        attributes={
            "program_name": program_name,
            "parameters": parameters,
        },
    )


def _build_compute_statement(node: ParseNode) -> StatementNode:
    target_var = _find_child_value(node, "TARGET")
    expression = _build_expression(_find_child_node(node, "EXPRESSION"))
    return StatementNode(
        statement_type=StatementType.COMPUTE,
        attributes={
            "target": VariableNode(variable_name=target_var or ""),
            "expression": expression,
        },
    )


def _build_move_statement(node: ParseNode) -> StatementNode:
    source_name = _find_child_value(node, "SOURCE")
    target_name = _find_child_value(node, "TARGET")
    return StatementNode(
        statement_type=StatementType.MOVE,
        attributes={
            "source": VariableNode(variable_name=source_name or ""),
            "target": VariableNode(variable_name=target_name or ""),
        },
    )


def _build_add_statement(node: ParseNode) -> StatementNode:
    value_node = _find_child_value(node, "VALUE")
    target_name = _find_child_value(node, "TARGET")
    literal = _create_literal(value_node)
    return StatementNode(
        statement_type=StatementType.ADD,
        attributes={
            "value": literal,
            "target": VariableNode(variable_name=target_name or ""),
        },
    )


def _build_evaluate_statement(node: ParseNode) -> StatementNode:
    expression_value = _find_child_value(node, "EXPRESSION")
    when_clauses_node = _find_child_node(node, "WHEN_CLAUSES")
    other_statements_node = _find_child_node(node, "STATEMENTS")

    when_clauses: list[dict[str, Any]] = []
    if when_clauses_node:
        for clause in when_clauses_node.children:
            if isinstance(clause, ParseNode) and clause.node_type == "WHEN_CLAUSE":
                when_value = _find_child_value(clause, "VALUE")
                clause_statements = _build_statements(_find_child_node(clause, "STATEMENTS"))
                when_clauses.append(
                    {"value": _create_literal(when_value), "statements": clause_statements}
                )

    return StatementNode(
        statement_type=StatementType.EVALUATE,
        attributes={
            "expression": VariableNode(variable_name=expression_value or ""),
            "when_clauses": when_clauses,
            "default_statements": _build_statements(other_statements_node),
        },
    )


# ============================================================================
# Expression helpers
# ============================================================================


def _build_expression(node: ParseNode | None) -> ExpressionNode | None:
    if node is None:
        return None

    if node.node_type == "CONDITION":
        left_node = _find_child_node(node, "LEFT")
        operator_node = _find_child_node(node, "OPERATOR")
        right_node = _find_child_node(node, "RIGHT")
        expression = ExpressionNode(
            operator=operator_node.value if operator_node else None,
            left=_create_variable(left_node.value if left_node else None),
            right=_create_operand(right_node.value if right_node else None),
        )
        expression.children = [
            child
            for child in (expression.left, expression.right)
            if isinstance(child, VariableNode)
        ]
        return expression

    if node.node_type == "EXPRESSION":
        if node.children:
            left = _create_operand(_find_child_value(node, "LEFT"))
            right = _create_operand(_find_child_value(node, "RIGHT"))
            operator = _find_child_value(node, "OPERATOR")
            expression = ExpressionNode(operator=operator, left=left, right=right)
            expression.children = [
                child for child in (left, right) if isinstance(child, VariableNode | LiteralNode)
            ]
            return expression
        return ExpressionNode(value=node.value)

    logger.debug("Unhandled expression node type: %s", node.node_type)
    return None


def _create_operand(value: Any) -> VariableNode | LiteralNode | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return _create_literal(value)
    if isinstance(value, str):
        # Zero and space are represented as reserved keywords in COBOL
        if value.upper() in {"ZERO", "ZEROS"}:
            return _create_literal(0)
        if value.upper() in {"SPACE", "SPACES"}:
            return _create_literal(" ")
        return VariableNode(variable_name=value)
    return None


def _create_variable(value: Any) -> VariableNode | None:
    if isinstance(value, str):
        return VariableNode(variable_name=value)
    return None


def _create_literal(value: Any) -> LiteralNode:
    if isinstance(value, int | float):
        return LiteralNode(value=value, literal_type="NUMBER")
    return LiteralNode(value=str(value), literal_type="STRING")


# ============================================================================
# Parse tree navigation helpers
# ============================================================================


def _extract_program_name(node: ParseNode) -> str | None:
    program_id_node = _find_child_node(node, "PROGRAM_ID")
    return (
        program_id_node.value
        if program_id_node and isinstance(program_id_node.value, str)
        else None
    )


def _find_child_value(node: ParseNode, target_type: str) -> Any:
    target = _find_child_node(node, target_type)
    return target.value if target is not None else None


def _find_child_node(node: ParseNode, target_type: str, occurrence: int = 0) -> ParseNode | None:
    count = 0
    for child in node.children:
        if isinstance(child, ParseNode) and child.node_type == target_type:
            if count == occurrence:
                return child
            count += 1
        if isinstance(child, ParseNode):
            nested = _find_child_node(
                child, target_type, occurrence - count if occurrence >= count else 0
            )
            if nested:
                return nested
    return None


def _walk_nodes(node: ParseNode, target_types: set[str]) -> Iterable[ParseNode]:
    for child in node.children:
        if not isinstance(child, ParseNode):
            continue
        if child.node_type in target_types:
            yield child
        yield from _walk_nodes(child, target_types)

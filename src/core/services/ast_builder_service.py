"""Build Abstract Syntax Trees (AST) from COBOL parse trees.

The COBOL parser (see ``cobol_parser_antlr_service.py``) produces a generic parse tree built
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
from src.core.services.cobol_parser_antlr_service import ParseNode


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

        # ANTLR grammar uses SENTENCE nodes containing STATEMENT nodes
        # Look for SENTENCE nodes and extract statements from them
        statements: list[StatementNode] = []
        sentence_nodes = list(_walk_nodes(candidate, {"SENTENCE"}))
        logger.debug(f"Paragraph '{paragraph_name}': found {len(sentence_nodes)} SENTENCE nodes")

        for sentence_node in sentence_nodes:
            sentence_statements = _build_statements_from_sentence(sentence_node)
            logger.debug(f"  SENTENCE yielded {len(sentence_statements)} statements")
            statements.extend(sentence_statements)

        paragraph = ParagraphNode(paragraph_name=paragraph_name, statements=statements)
        paragraph.children = list(statements)
        paragraphs.append(paragraph)
    return paragraphs


def _build_statements_from_sentence(sentence_node: ParseNode) -> list[StatementNode]:
    """Extract STATEMENT nodes from a SENTENCE node.

    ANTLR grammar structure: SENTENCE → STATEMENT → (specific statement type)
    The STATEMENT node is a wrapper; we need to look at its children for the actual statement type.
    """
    statements: list[StatementNode] = []
    for statement_wrapper in _walk_nodes(sentence_node, {"STATEMENT"}):
        # STATEMENT is a wrapper node - look at its children for the actual statement type
        for child in statement_wrapper.children:
            if isinstance(child, ParseNode):
                statement = _build_statement(child)
                if statement:
                    statements.append(statement)
    return statements


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
    """Build PERFORM statement from ANTLR parse tree.

    ANTLR structure:
    PERFORMSTATEMENT → PERFORMPROCEDURESTATEMENT
        └─ PROCEDURENAME (value already extracted by ANTLR parser)
           └─ PARAGRAPH_NAME
              └─ COBOLWORD
                 └─ IDENTIFIER (terminal with paragraph name)

    Note: The ANTLR parser's _extract_value_from_children() function already
    extracts the paragraph name and stores it in PROCEDURENAME.value, so we
    can use that directly instead of drilling down through children.
    """
    # Find PERFORMPROCEDURESTATEMENT
    perform_proc = _find_child_node(node, "PERFORMPROCEDURESTATEMENT")
    if not perform_proc:
        logger.warning("PERFORM statement missing PERFORMPROCEDURESTATEMENT node")
        return StatementNode(
            statement_type=StatementType.PERFORM,
            attributes={"target_paragraph": ""},
        )

    # Find PROCEDURENAME - the value is already extracted by ANTLR parser
    procedure_name = _find_child_node(perform_proc, "PROCEDURENAME")
    if not procedure_name:
        logger.warning("PERFORM statement missing PROCEDURENAME node")
        return StatementNode(
            statement_type=StatementType.PERFORM,
            attributes={"target_paragraph": ""},
        )

    # Use the value directly from PROCEDURENAME (already extracted by ANTLR)
    target_paragraph = str(procedure_name.value) if procedure_name.value else ""

    if not target_paragraph:
        logger.warning("PERFORM statement has empty target paragraph name")

    return StatementNode(
        statement_type=StatementType.PERFORM,
        attributes={"target_paragraph": target_paragraph},
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
    """Build IF statement from ANTLR parse tree.

    ANTLR structure:
    IFSTATEMENT
        ├─ CONDITION
        ├─ IFTHEN
        │  └─ STATEMENT (wrapper for actual statements)
        └─ IFELSE (optional)
           └─ STATEMENT (wrapper for actual statements)
    """
    # Extract condition
    condition_node = _find_child_node(node, "CONDITION")
    condition = _build_expression(condition_node)

    # Extract THEN statements
    ifthen_node = _find_child_node(node, "IFTHEN")
    then_statements: list[StatementNode] = []
    if ifthen_node:
        # IFTHEN contains STATEMENT wrappers
        for stmt_node in _walk_nodes(ifthen_node, {"STATEMENT"}):
            # Extract statement from wrapper (same as sentence handling)
            for child in stmt_node.children:
                if isinstance(child, ParseNode):
                    stmt = _build_statement(child)
                    if stmt:
                        then_statements.append(stmt)

    # Check for ELSE branch
    ifelse_node = _find_child_node(node, "IFELSE")
    if ifelse_node:
        # This is actually an IF-ELSE statement
        else_statements: list[StatementNode] = []
        for stmt_node in _walk_nodes(ifelse_node, {"STATEMENT"}):
            for child in stmt_node.children:
                if isinstance(child, ParseNode):
                    stmt = _build_statement(child)
                    if stmt:
                        else_statements.append(stmt)
        return StatementNode(
            statement_type=StatementType.IF,
            attributes={
                "condition": condition,
                "then_statements": then_statements,
                "else_statements": else_statements,
            },
        )

    # No ELSE branch
    return StatementNode(
        statement_type=StatementType.IF,
        attributes={
            "condition": condition,
            "then_statements": then_statements,
        },
    )


def _build_if_else_statement(node: ParseNode) -> StatementNode:
    """Build IF-ELSE statement (delegates to _build_if_statement).

    The ANTLR grammar represents IF-ELSE with a single IFSTATEMENT node
    that contains both IFTHEN and IFELSE children, so we use the same
    builder function.
    """
    return _build_if_statement(node)


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
    """Build MOVE statement from ANTLR parse tree.

    ANTLR structure:
    MOVESTATEMENT → MOVETOSTATEMENT
        ├─ MOVETOSENDINGAREA (source)
        │  ├─ LITERAL (if literal source)
        │  └─ IDENTIFIER (if variable source)
        └─ IDENTIFIER (target)
    """
    # Find MOVETOSTATEMENT
    movetostatement = _find_child_node(node, "MOVETOSTATEMENT")
    if not movetostatement:
        logger.warning("MOVE statement missing MOVETOSTATEMENT node")
        return StatementNode(
            statement_type=StatementType.MOVE,
            attributes={
                "source": VariableNode(variable_name=""),
                "target": VariableNode(variable_name=""),
            },
        )

    # Extract source (from MOVETOSENDINGAREA)
    source_literal = _extract_literal_from_sending_area(movetostatement)
    source_identifier = _extract_identifier_from_sending_area(movetostatement)

    source: VariableNode | LiteralNode
    if source_literal:
        # It's a literal - extract value and create LiteralNode
        source_value = _extract_literal_value(source_literal)
        source = _create_literal(source_value)
    elif source_identifier:
        # It's a variable - extract name
        source_name = _extract_variable_name(source_identifier)
        source = VariableNode(variable_name=source_name or "")
    else:
        logger.warning("MOVE statement missing source (neither literal nor identifier)")
        source = VariableNode(variable_name="")

    # Extract target (direct IDENTIFIER child of MOVETOSTATEMENT)
    target_identifier = _find_child_node(movetostatement, "IDENTIFIER")
    target_name = _extract_variable_name(target_identifier)
    target = VariableNode(variable_name=target_name or "")

    return StatementNode(
        statement_type=StatementType.MOVE,
        attributes={
            "source": source,
            "target": target,
        },
    )


def _build_add_statement(node: ParseNode) -> StatementNode:
    """Build ADD statement from ANTLR parse tree.

    ANTLR structure:
    ADDSTATEMENT → ADDTOSTATEMENT
        ├─ ADDFROM (value to add)
        │  └─ LITERAL (or IDENTIFIER for variable)
        └─ ADDTO (target variable)
           └─ IDENTIFIER
    """
    # Find ADDTOSTATEMENT
    addtostatement = _find_child_node(node, "ADDTOSTATEMENT")
    if not addtostatement:
        logger.warning("ADD statement missing ADDTOSTATEMENT node")
        return StatementNode(
            statement_type=StatementType.ADD,
            attributes={
                "value": _create_literal(0),
                "target": VariableNode(variable_name=""),
            },
        )

    # Extract value (from ADDFROM)
    addfrom = _find_child_node(addtostatement, "ADDFROM")
    if addfrom:
        # Check if it's a literal or identifier
        literal_node = _find_child_node(addfrom, "LITERAL")
        if literal_node:
            value = _extract_literal_value(literal_node)
            literal = _create_literal(value)
        else:
            # Could be a variable (IDENTIFIER)
            identifier_node = _find_child_node(addfrom, "IDENTIFIER")
            if identifier_node:
                var_name = _extract_variable_name(identifier_node)
                # For now, treat as literal (may need to revisit)
                literal = _create_literal(var_name or "0")
            else:
                literal = _create_literal(0)
    else:
        logger.warning("ADD statement missing ADDFROM node")
        literal = _create_literal(0)

    # Extract target (from ADDTO)
    addto = _find_child_node(addtostatement, "ADDTO")
    if addto:
        target_identifier = _find_child_node(addto, "IDENTIFIER")
        target_name = _extract_variable_name(target_identifier)
        target = VariableNode(variable_name=target_name or "")
    else:
        logger.warning("ADD statement missing ADDTO node")
        target = VariableNode(variable_name="")

    return StatementNode(
        statement_type=StatementType.ADD,
        attributes={
            "value": literal,
            "target": target,
        },
    )


def _extract_evaluate_condition_value(when_condition: ParseNode | None) -> Any:
    """Extract condition value from EVALUATEWHEN node.

    Args:
        when_condition: EVALUATEWHEN node or None

    Returns:
        Condition value (literal or variable name) or None
    """
    if not when_condition:
        return None

    evaluate_condition = _find_child_node(when_condition, "EVALUATECONDITION")
    if not evaluate_condition:
        return None

    evaluate_value = _find_child_node(evaluate_condition, "EVALUATEVALUE")
    if not evaluate_value:
        return None

    # Could be literal or identifier - try both
    literal_node = _find_child_node(evaluate_value, "LITERAL")
    if literal_node:
        return _extract_literal_value(literal_node)

    identifier_node = _find_child_node(evaluate_value, "IDENTIFIER")
    if identifier_node:
        return _extract_variable_name(identifier_node)

    return None


def _extract_statements_from_node(node: ParseNode | None) -> list[StatementNode]:
    """Extract statements from a node containing STATEMENT children.

    Args:
        node: Node containing STATEMENT nodes, or None

    Returns:
        List of StatementNode objects
    """
    if not node:
        return []

    statements: list[StatementNode] = []
    for stmt_node in _walk_nodes(node, {"STATEMENT"}):
        for child in stmt_node.children:
            if isinstance(child, ParseNode):
                stmt = _build_statement(child)
                if stmt:
                    statements.append(stmt)
    return statements


def _build_evaluate_statement(node: ParseNode) -> StatementNode:
    """Build EVALUATE statement from ANTLR parse tree.

    ANTLR structure:
    EVALUATESTATEMENT
        ├─ EVALUATESELECT (expression being evaluated)
        │  └─ IDENTIFIER
        ├─ EVALUATEWHENPHRASE (one or more WHEN clauses)
        │  ├─ EVALUATEWHEN
        │  │  └─ EVALUATECONDITION
        │  │     └─ EVALUATEVALUE
        │  └─ STATEMENT (action for this WHEN)
        └─ EVALUATEWHENOTHER (optional default clause)
           └─ STATEMENT (default action)
    """
    # Extract the expression being evaluated
    evaluate_select = _find_child_node(node, "EVALUATESELECT")
    expression_value = ""
    if evaluate_select:
        select_identifier = _find_child_node(evaluate_select, "IDENTIFIER")
        if select_identifier:
            expression_value = _extract_variable_name(select_identifier) or ""

    # Extract WHEN clauses
    when_clauses: list[dict[str, Any]] = []
    for when_phrase in _walk_nodes(node, {"EVALUATEWHENPHRASE"}):
        when_condition = _find_child_node(when_phrase, "EVALUATEWHEN")
        condition_value = _extract_evaluate_condition_value(when_condition)
        statements = _extract_statements_from_node(when_phrase)

        when_clauses.append({"value": _create_literal(condition_value), "statements": statements})

    # Extract WHEN OTHER (default) clause
    when_other = _find_child_node(node, "EVALUATEWHENOTHER")
    default_statements = _extract_statements_from_node(when_other)

    return StatementNode(
        statement_type=StatementType.EVALUATE,
        attributes={
            "expression": VariableNode(variable_name=expression_value or ""),
            "when_clauses": when_clauses,
            "default_statements": default_statements,
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


def _extract_variable_name(identifier_node: ParseNode | None) -> str | None:
    """Extract variable name from an IDENTIFIER node.

    ANTLR grammar path for variable names:
    IDENTIFIER → QUALIFIEDDATANAME → QUALIFIEDDATANAMEFORMAT1
                → DATANAME → COBOLWORD → IDENTIFIER (terminal with value)

    Args:
        identifier_node: IDENTIFIER node from parse tree

    Returns:
        Variable name string, or None if not found
    """
    if identifier_node is None:
        return None

    # Try to find DATANAME node (most reliable path)
    dataname_node = _find_child_node(identifier_node, "DATANAME")
    if dataname_node:
        # Navigate: DATANAME → COBOLWORD → IDENTIFIER (terminal)
        cobol_word = _find_child_node(dataname_node, "COBOLWORD")
        if cobol_word:
            terminal_identifier = _find_child_node(cobol_word, "IDENTIFIER")
            if terminal_identifier and terminal_identifier.value:
                return str(terminal_identifier.value)

    # Fallback: try COBOLWORD directly
    cobol_word = _find_child_node(identifier_node, "COBOLWORD")
    if cobol_word:
        terminal_identifier = _find_child_node(cobol_word, "IDENTIFIER")
        if terminal_identifier and terminal_identifier.value:
            return str(terminal_identifier.value)

    # Last resort: check if this node itself has a value
    if identifier_node.value and isinstance(identifier_node.value, str):
        return str(identifier_node.value)

    return None


def _parse_numeric_literal(numeric_literal: ParseNode) -> float | int | str:
    """Parse numeric literal value.

    Args:
        numeric_literal: NUMERICLITERAL node

    Returns:
        Parsed number (float/int) or string if parsing fails
    """
    value_str = str(numeric_literal.value)
    try:
        return float(value_str) if "." in value_str else int(value_str)
    except ValueError:
        return value_str


def _parse_nonnumeric_literal(nonnumeric_literal: ParseNode) -> str:
    """Parse non-numeric literal value, removing quotes if present.

    Args:
        nonnumeric_literal: NONNUMERICLITERAL node

    Returns:
        String value with quotes removed
    """
    value = str(nonnumeric_literal.value)
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    return value


def _extract_literal_value(literal_node: ParseNode | None) -> Any:
    """Extract value from a LITERAL node.

    ANTLR grammar structure:
    LITERAL → NONNUMERICLITERAL (for strings)
    LITERAL → NUMERICLITERAL (for numbers)

    Args:
        literal_node: LITERAL node from parse tree

    Returns:
        The literal value (string or number), or None if not found
    """
    if literal_node is None:
        return None

    # Check for numeric literal
    numeric_literal = _find_child_node(literal_node, "NUMERICLITERAL")
    if numeric_literal and numeric_literal.value:
        return _parse_numeric_literal(numeric_literal)

    # Check for non-numeric (string) literal
    nonnumeric_literal = _find_child_node(literal_node, "NONNUMERICLITERAL")
    if nonnumeric_literal and nonnumeric_literal.value:
        return _parse_nonnumeric_literal(nonnumeric_literal)

    # Fallback: check if literal node itself has a value
    return literal_node.value if literal_node.value else None


def _extract_identifier_from_sending_area(movetostatement_node: ParseNode) -> ParseNode | None:
    """Extract IDENTIFIER node from MOVETOSENDINGAREA.

    Helper for MOVE statement source extraction.

    Args:
        movetostatement_node: MOVETOSTATEMENT node

    Returns:
        IDENTIFIER node or None if not found (might be a LITERAL instead)
    """
    sending_area = _find_child_node(movetostatement_node, "MOVETOSENDINGAREA")
    if sending_area:
        return _find_child_node(sending_area, "IDENTIFIER")
    return None


def _extract_literal_from_sending_area(movetostatement_node: ParseNode) -> ParseNode | None:
    """Extract LITERAL node from MOVETOSENDINGAREA.

    Helper for MOVE statement source extraction when source is a literal.

    Args:
        movetostatement_node: MOVETOSTATEMENT node

    Returns:
        LITERAL node or None if not found (might be an IDENTIFIER instead)
    """
    sending_area = _find_child_node(movetostatement_node, "MOVETOSENDINGAREA")
    if sending_area:
        return _find_child_node(sending_area, "LITERAL")
    return None

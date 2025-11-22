"""Tests for the COBOL CFG builder."""

import pytest

from src.core.models.cobol_analysis_model import (
    CFGEdgeType,
    ControlFlowNode,
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
from src.core.services.cobol_analysis.cfg_builder_service import CFGBuilderError, build_cfg


def _create_program_with_if() -> ProgramNode:
    program = ProgramNode(program_name="SAMPLE")

    identification_division = DivisionNode(division_type=DivisionType.IDENTIFICATION)

    procedure_division = DivisionNode(division_type=DivisionType.PROCEDURE)

    if_statement = StatementNode(
        statement_type=StatementType.IF,
        attributes={
            "condition": ExpressionNode(
                operator="<",
                left=VariableNode(variable_name="BALANCE"),
                right=LiteralNode(value=0, literal_type="NUMBER"),
            ),
            "then_statements": [
                StatementNode(
                    statement_type=StatementType.DISPLAY,
                    attributes={"message": LiteralNode(value="NEGATIVE", literal_type="STRING")},
                )
            ],
            "else_statements": [
                StatementNode(
                    statement_type=StatementType.MOVE,
                    attributes={
                        "source": VariableNode(variable_name="BALANCE"),
                        "target": VariableNode(variable_name="AVAILABLE"),
                    },
                )
            ],
        },
    )

    main_paragraph = ParagraphNode(
        paragraph_name="MAIN",
        statements=[
            StatementNode(
                statement_type=StatementType.MOVE,
                attributes={
                    "source": VariableNode(variable_name="INPUT-AMOUNT"),
                    "target": VariableNode(variable_name="BALANCE"),
                },
            ),
            if_statement,
        ],
    )

    procedure_section = SectionNode(
        section_name="PROC",
        paragraphs=[main_paragraph],
    )
    procedure_division.sections = [procedure_section]

    program.divisions = [identification_division, procedure_division]

    return program


def _create_program_with_perform() -> ProgramNode:
    program = ProgramNode(program_name="PERFORM_SAMPLE")

    identification_division = DivisionNode(division_type=DivisionType.IDENTIFICATION)
    procedure_division = DivisionNode(division_type=DivisionType.PROCEDURE)

    perform_paragraph = ParagraphNode(
        paragraph_name="CALLER",
        statements=[
            StatementNode(
                statement_type=StatementType.PERFORM,
                attributes={"target_paragraph": "CALLEE"},
            )
        ],
    )

    callee_paragraph = ParagraphNode(
        paragraph_name="CALLEE",
        statements=[
            StatementNode(
                statement_type=StatementType.DISPLAY,
                attributes={"message": LiteralNode(value="CALLED", literal_type="STRING")},
            )
        ],
    )

    procedure_section = SectionNode(
        section_name="PROC", paragraphs=[perform_paragraph, callee_paragraph]
    )
    procedure_division.sections = [procedure_section]
    program.divisions = [identification_division, procedure_division]

    return program


def test_build_cfg_handles_if_branching() -> None:
    program = _create_program_with_if()

    cfg = build_cfg(program)

    node_ids = {node.node_id for node in cfg.nodes}
    assert "paragraph_MAIN" in node_ids
    assert any(
        isinstance(node, ControlFlowNode) and node.node_id.startswith("if_MAIN_")
        for node in cfg.nodes
    )

    edge_signatures = {
        (edge.source.node_id, edge.target.node_id, edge.edge_type) for edge in cfg.edges
    }
    assert ("entry", "paragraph_MAIN", CFGEdgeType.SEQUENTIAL) in edge_signatures
    assert any(edge_type == CFGEdgeType.TRUE for _, _, edge_type in edge_signatures)
    assert any(edge_type == CFGEdgeType.FALSE for _, _, edge_type in edge_signatures)


def test_build_cfg_handles_perform_statements() -> None:
    program = _create_program_with_perform()

    cfg = build_cfg(program)

    node_ids = {node.node_id for node in cfg.nodes}
    assert "paragraph_CALLER" in node_ids
    assert "paragraph_CALLEE" in node_ids
    assert any(
        isinstance(node, ControlFlowNode) and node.node_id.startswith("perform_CALLER_")
        for node in cfg.nodes
    )

    edge_signatures = {
        (edge.source.node_id, edge.target.node_id, edge.edge_type) for edge in cfg.edges
    }
    assert ("entry", "paragraph_CALLER", CFGEdgeType.SEQUENTIAL) in edge_signatures
    assert any(edge_type == CFGEdgeType.CALL for _, _, edge_type in edge_signatures)
    assert any(edge_type == CFGEdgeType.RETURN for _, _, edge_type in edge_signatures)


def test_build_cfg_requires_procedure_division() -> None:
    program = ProgramNode(program_name="NO_PROC")

    with pytest.raises(CFGBuilderError):
        build_cfg(program)


def _create_program_with_goto() -> ProgramNode:
    """Create a program with GOTO statement."""
    program = ProgramNode(program_name="GOTO_SAMPLE")

    identification_division = DivisionNode(division_type=DivisionType.IDENTIFICATION)
    procedure_division = DivisionNode(division_type=DivisionType.PROCEDURE)

    goto_statement = StatementNode(
        statement_type=StatementType.GOTO,
        attributes={"target_paragraph": "END-PARAGRAPH"},
    )

    main_paragraph = ParagraphNode(
        paragraph_name="MAIN",
        statements=[
            StatementNode(
                statement_type=StatementType.DISPLAY,
                attributes={"message": LiteralNode(value="Before GOTO", literal_type="STRING")},
            ),
            goto_statement,
            StatementNode(
                statement_type=StatementType.DISPLAY,
                attributes={"message": LiteralNode(value="After GOTO", literal_type="STRING")},
            ),
        ],
    )

    end_paragraph = ParagraphNode(
        paragraph_name="END-PARAGRAPH",
        statements=[
            StatementNode(
                statement_type=StatementType.STOP,
                attributes={},
            )
        ],
    )

    procedure_section = SectionNode(
        section_name="PROC",
        paragraphs=[main_paragraph, end_paragraph],
    )
    procedure_division.sections = [procedure_section]
    program.divisions = [identification_division, procedure_division]

    return program


def test_build_cfg_handles_goto_statements() -> None:
    """Test CFG builder handles GOTO statements."""
    program = _create_program_with_goto()

    cfg = build_cfg(program)

    edge_signatures = {
        (edge.source.node_id, edge.target.node_id, edge.edge_type) for edge in cfg.edges
    }

    # Should have GOTO edge from MAIN to END-PARAGRAPH
    assert any(
        edge_type == CFGEdgeType.GOTO
        for source_id, target_id, edge_type in edge_signatures
        if "MAIN" in source_id and "END-PARAGRAPH" in target_id
    )


def _create_program_with_nested_if() -> ProgramNode:
    """Create a program with nested IF statements."""
    program = ProgramNode(program_name="NESTED_IF_SAMPLE")

    identification_division = DivisionNode(division_type=DivisionType.IDENTIFICATION)
    procedure_division = DivisionNode(division_type=DivisionType.PROCEDURE)

    inner_if = StatementNode(
        statement_type=StatementType.IF,
        attributes={
            "condition": ExpressionNode(
                operator=">",
                left=VariableNode(variable_name="VALUE2"),
                right=LiteralNode(value=10, literal_type="NUMBER"),
            ),
            "then_statements": [
                StatementNode(
                    statement_type=StatementType.DISPLAY,
                    attributes={"message": LiteralNode(value="Inner true", literal_type="STRING")},
                )
            ],
        },
    )

    outer_if = StatementNode(
        statement_type=StatementType.IF,
        attributes={
            "condition": ExpressionNode(
                operator="<",
                left=VariableNode(variable_name="VALUE1"),
                right=LiteralNode(value=0, literal_type="NUMBER"),
            ),
            "then_statements": [inner_if],
        },
    )

    paragraph = ParagraphNode(
        paragraph_name="MAIN",
        statements=[outer_if],
    )

    procedure_section = SectionNode(section_name="PROC", paragraphs=[paragraph])
    procedure_division.sections = [procedure_section]
    program.divisions = [identification_division, procedure_division]

    return program


def test_build_cfg_handles_nested_conditionals() -> None:
    """Test CFG builder handles nested IF statements."""
    program = _create_program_with_nested_if()

    cfg = build_cfg(program)

    # Should have control flow nodes for nested conditionals
    control_flow_nodes = [node for node in cfg.nodes if isinstance(node, ControlFlowNode)]
    assert len(control_flow_nodes) >= 1  # At least outer IF (inner IF may be handled differently)

    # Should have true/false edges for conditionals
    edge_signatures = {
        (edge.source.node_id, edge.target.node_id, edge.edge_type) for edge in cfg.edges
    }
    true_edges = [edge_type for _, _, edge_type in edge_signatures if edge_type == CFGEdgeType.TRUE]
    false_edges = [
        edge_type for _, _, edge_type in edge_signatures if edge_type == CFGEdgeType.FALSE
    ]
    assert len(true_edges) >= 1  # At least one true branch
    assert len(false_edges) >= 1  # At least one false branch


def _create_program_with_loop() -> ProgramNode:
    """Create a program with PERFORM UNTIL loop."""
    program = ProgramNode(program_name="LOOP_SAMPLE")

    identification_division = DivisionNode(division_type=DivisionType.IDENTIFICATION)
    procedure_division = DivisionNode(division_type=DivisionType.PROCEDURE)

    loop_body = ParagraphNode(
        paragraph_name="LOOP-BODY",
        statements=[
            StatementNode(
                statement_type=StatementType.DISPLAY,
                attributes={"message": LiteralNode(value="Looping", literal_type="STRING")},
            ),
            StatementNode(
                statement_type=StatementType.COMPUTE,
                attributes={
                    "target": VariableNode(variable_name="COUNTER"),
                    "expression": ExpressionNode(
                        operator="+",
                        left=VariableNode(variable_name="COUNTER"),
                        right=LiteralNode(value=1, literal_type="NUMBER"),
                    ),
                },
            ),
        ],
    )

    perform_until = StatementNode(
        statement_type=StatementType.PERFORM,
        attributes={
            "target_paragraph": "LOOP-BODY",
            "until_condition": ExpressionNode(
                operator=">",
                left=VariableNode(variable_name="COUNTER"),
                right=LiteralNode(value=10, literal_type="NUMBER"),
            ),
        },
    )

    main_paragraph = ParagraphNode(
        paragraph_name="MAIN",
        statements=[perform_until],
    )

    procedure_section = SectionNode(
        section_name="PROC",
        paragraphs=[main_paragraph, loop_body],
    )
    procedure_division.sections = [procedure_section]
    program.divisions = [identification_division, procedure_division]

    return program


def test_build_cfg_handles_loop_structures() -> None:
    """Test CFG builder handles PERFORM UNTIL loops."""
    program = _create_program_with_loop()

    cfg = build_cfg(program)

    node_ids = {node.node_id for node in cfg.nodes}
    assert "paragraph_MAIN" in node_ids
    assert "paragraph_LOOP-BODY" in node_ids

    # Should have edges connecting loop body
    edge_signatures = {
        (edge.source.node_id, edge.target.node_id, edge.edge_type) for edge in cfg.edges
    }
    # Should have call edge to loop body and return edge back
    assert any(edge_type == CFGEdgeType.CALL for _, _, edge_type in edge_signatures)
    assert any(edge_type == CFGEdgeType.RETURN for _, _, edge_type in edge_signatures)

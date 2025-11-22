"""Tests for the COBOL DFG builder."""

import pytest

from src.core.models.cobol_analysis_model import (
    ControlFlowGraph,
    DataFlowGraph,
    DFGEdgeType,
    DivisionNode,
    DivisionType,
    ExpressionNode,
    LiteralNode,
    ParagraphNode,
    ProgramNode,
    SectionNode,
    StatementNode,
    StatementType,
    VariableDefNode,
    VariableNode,
    VariableUseNode,
)
from src.core.services.cobol_analysis.cfg_builder_service import build_cfg
from src.core.services.cobol_analysis.dfg_builder_service import DFGBuilderError, build_dfg


def _create_program_with_data_flow() -> ProgramNode:
    program = ProgramNode(program_name="DATA_FLOW_SAMPLE")

    identification_division = DivisionNode(division_type=DivisionType.IDENTIFICATION)
    procedure_division = DivisionNode(division_type=DivisionType.PROCEDURE)

    move_statement = StatementNode(
        statement_type=StatementType.MOVE,
        attributes={
            "source": VariableNode(variable_name="INPUT-AMOUNT"),
            "target": VariableNode(variable_name="BALANCE"),
        },
    )

    compute_statement = StatementNode(
        statement_type=StatementType.COMPUTE,
        attributes={
            "target": VariableNode(variable_name="TOTAL"),
            "expression": ExpressionNode(
                operator="+",
                left=VariableNode(variable_name="BALANCE"),
                right=LiteralNode(value=100, literal_type="NUMBER"),
            ),
        },
    )

    if_statement = StatementNode(
        statement_type=StatementType.IF,
        attributes={
            "condition": ExpressionNode(
                operator=">",
                left=VariableNode(variable_name="TOTAL"),
                right=VariableNode(variable_name="LIMIT"),
            ),
            "then_statements": [
                StatementNode(
                    statement_type=StatementType.DISPLAY,
                    attributes={"message": LiteralNode(value="OVER", literal_type="STRING")},
                )
            ],
            "else_statements": [
                StatementNode(
                    statement_type=StatementType.MOVE,
                    attributes={
                        "source": VariableNode(variable_name="TOTAL"),
                        "target": VariableNode(variable_name="AVAILABLE"),
                    },
                )
            ],
        },
    )

    paragraph = ParagraphNode(
        paragraph_name="MAIN",
        statements=[move_statement, compute_statement, if_statement],
    )

    procedure_division.sections = [SectionNode(section_name="PROC", paragraphs=[paragraph])]
    program.divisions = [identification_division, procedure_division]

    return program


def test_build_dfg_captures_def_use_edges() -> None:
    program = _create_program_with_data_flow()
    cfg = build_cfg(program)

    dfg = build_dfg(program, cfg)

    assert isinstance(dfg, DataFlowGraph)
    def_nodes = {node.node_id: node for node in dfg.nodes if isinstance(node, VariableDefNode)}
    use_nodes = {node.node_id: node for node in dfg.nodes if isinstance(node, VariableUseNode)}

    balance_def_id = next(
        node_id for node_id, node in def_nodes.items() if node.variable_name == "BALANCE"
    )
    total_def_id = next(
        node_id for node_id, node in def_nodes.items() if node.variable_name == "TOTAL"
    )
    balance_use_id = next(
        node_id for node_id, node in use_nodes.items() if node.variable_name == "BALANCE"
    )
    total_use_id = next(
        node_id for node_id, node in use_nodes.items() if node.variable_name == "TOTAL"
    )

    edge_signatures = {
        (edge.source.node_id, edge.target.node_id, edge.edge_type) for edge in dfg.edges
    }

    assert (balance_def_id, balance_use_id, DFGEdgeType.DEF_USE) in edge_signatures
    assert (total_def_id, total_use_id, DFGEdgeType.DEF_USE) in edge_signatures


def test_build_dfg_requires_procedure_division() -> None:
    program = ProgramNode(program_name="NO_PROC")

    with pytest.raises(DFGBuilderError):
        build_dfg(program, ControlFlowGraph(entry_node=None, exit_node=None))  # type: ignore[arg-type]


def _create_program_with_file_io() -> ProgramNode:
    """Create a program with file I/O operations (READ → PROCESS → WRITE)."""
    program = ProgramNode(program_name="FILE_IO_SAMPLE")

    identification_division = DivisionNode(division_type=DivisionType.IDENTIFICATION)
    procedure_division = DivisionNode(division_type=DivisionType.PROCEDURE)

    # READ statement - reads data into INPUT-RECORD
    read_statement = StatementNode(
        statement_type=StatementType.READ,
        attributes={
            "file_name": "INPUT-FILE",
            "into": VariableNode(variable_name="INPUT-RECORD"),
        },
    )

    # PROCESS - MOVE data from INPUT-RECORD to WORKING-STORAGE
    move_statement = StatementNode(
        statement_type=StatementType.MOVE,
        attributes={
            "source": VariableNode(variable_name="INPUT-RECORD"),
            "target": VariableNode(variable_name="WS-RECORD"),
        },
    )

    # COMPUTE - process the data
    compute_statement = StatementNode(
        statement_type=StatementType.COMPUTE,
        attributes={
            "target": VariableNode(variable_name="WS-TOTAL"),
            "expression": ExpressionNode(
                operator="+",
                left=VariableNode(variable_name="WS-RECORD"),
                right=LiteralNode(value=100, literal_type="NUMBER"),
            ),
        },
    )

    # WRITE statement - writes processed data
    write_statement = StatementNode(
        statement_type=StatementType.WRITE,
        attributes={
            "file_name": "OUTPUT-FILE",
            "from": VariableNode(variable_name="WS-TOTAL"),
        },
    )

    paragraph = ParagraphNode(
        paragraph_name="MAIN",
        statements=[read_statement, move_statement, compute_statement, write_statement],
    )

    procedure_division.sections = [SectionNode(section_name="PROC", paragraphs=[paragraph])]
    program.divisions = [identification_division, procedure_division]

    return program


def test_build_dfg_handles_file_io_pattern() -> None:
    """Test DFG builder handles file I/O pattern (READ → PROCESS → WRITE)."""
    program = _create_program_with_file_io()
    cfg = build_cfg(program)

    dfg = build_dfg(program, cfg)

    # Should have def nodes for variables written to
    def_nodes = {
        node.variable_name: node for node in dfg.nodes if isinstance(node, VariableDefNode)
    }

    # Should have use nodes for variables read from
    use_nodes = {
        node.variable_name: node for node in dfg.nodes if isinstance(node, VariableUseNode)
    }

    # Verify data flow: INPUT-RECORD → WS-RECORD → WS-TOTAL
    assert "INPUT-RECORD" in def_nodes or "INPUT-RECORD" in use_nodes
    assert "WS-RECORD" in def_nodes or "WS-RECORD" in use_nodes
    assert "WS-TOTAL" in def_nodes or "WS-TOTAL" in use_nodes

    # Verify def-use edges exist
    edge_signatures = {
        (edge.source.node_id, edge.target.node_id, edge.edge_type) for edge in dfg.edges
    }
    assert any(edge_type == DFGEdgeType.DEF_USE for _, _, edge_type in edge_signatures)

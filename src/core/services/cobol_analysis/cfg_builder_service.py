"""Build Control Flow Graphs (CFG) from COBOL AST structures."""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.core.models.cobol_analysis_model import (
    BasicBlock,
    CFGEdge,
    CFGEdgeType,
    ControlFlowGraph,
    ControlFlowNode,
    DivisionNode,
    DivisionType,
    EntryNode,
    ExitNode,
    ParagraphNode,
    ProgramNode,
    SectionNode,
    StatementNode,
    StatementType,
)


logger = logging.getLogger(__name__)


class CFGBuilderError(ValueError):
    """Raised when the CFG cannot be constructed from the provided AST."""


def build_cfg(ast: ProgramNode) -> ControlFlowGraph:
    """Build a control flow graph from a COBOL AST.

    Args:
        ast: ProgramNode representing the AST root.

    Returns:
        ControlFlowGraph containing nodes and edges for the program.

    Raises:
        CFGBuilderError: If the AST is missing required procedure information.
    """
    if not isinstance(ast, ProgramNode):
        raise CFGBuilderError("AST root must be a ProgramNode.")

    procedure_division = _find_procedure_division(ast.divisions)
    if procedure_division is None:
        raise CFGBuilderError("Procedure division is required to build CFG.")

    paragraphs = _collect_paragraphs(procedure_division.sections)
    if not paragraphs:
        raise CFGBuilderError("Procedure division must contain at least one paragraph.")

    entry_node = EntryNode()
    exit_node = ExitNode()
    graph = ControlFlowGraph(entry_node=entry_node, exit_node=exit_node)
    graph.add_node(entry_node)
    graph.add_node(exit_node)

    paragraph_blocks = _create_paragraph_blocks(graph, paragraphs)

    first_paragraph = paragraphs[0]
    graph.add_edge(
        CFGEdge(
            source=entry_node,
            target=paragraph_blocks[first_paragraph.paragraph_name],
            edge_type=CFGEdgeType.SEQUENTIAL,
        )
    )

    for index, paragraph in enumerate(paragraphs):
        block = paragraph_blocks[paragraph.paragraph_name]
        fallback_target = (
            paragraph_blocks[paragraphs[index + 1].paragraph_name]
            if index + 1 < len(paragraphs)
            else exit_node
        )
        _process_paragraph(
            graph=graph,
            paragraph=paragraph,
            block=block,
            paragraph_blocks=paragraph_blocks,
            fallback_target=fallback_target,
        )

    return graph


def _find_procedure_division(divisions: list[DivisionNode]) -> DivisionNode | None:
    for division in divisions:
        if division.division_type == DivisionType.PROCEDURE:
            return division
    return None


def _collect_paragraphs(sections: list[SectionNode]) -> list[ParagraphNode]:
    paragraphs: list[ParagraphNode] = []
    for section in sections:
        paragraphs.extend(section.paragraphs)
    return [paragraph for paragraph in paragraphs if paragraph.paragraph_name]


def _create_paragraph_blocks(
    graph: ControlFlowGraph, paragraphs: list[ParagraphNode]
) -> dict[str, BasicBlock]:
    blocks: dict[str, BasicBlock] = {}
    for index, paragraph in enumerate(paragraphs):
        node_id = f"paragraph_{paragraph.paragraph_name or index}"
        block = BasicBlock(
            node_id=node_id,
            label=paragraph.paragraph_name or node_id,
            statements=paragraph.statements,
        )
        blocks[paragraph.paragraph_name] = block
        graph.add_node(block)
    return blocks


def _process_paragraph(
    graph: ControlFlowGraph,
    paragraph: ParagraphNode,
    block: BasicBlock,
    paragraph_blocks: dict[str, BasicBlock],
    fallback_target: BasicBlock | ExitNode,
) -> None:
    if not paragraph.statements:
        graph.add_edge(
            CFGEdge(source=block, target=fallback_target, edge_type=CFGEdgeType.SEQUENTIAL)
        )
        return

    handlers: dict[StatementType, Callable[[int, StatementNode], None]] = {
        StatementType.IF: lambda idx, stmt: _handle_if_statement(
            graph,
            block,
            paragraph.paragraph_name,
            idx,
            stmt,
            fallback_target,
        ),
        StatementType.PERFORM: lambda idx, stmt: _handle_perform_statement(
            graph,
            block,
            paragraph.paragraph_name,
            idx,
            stmt,
            paragraph_blocks,
            fallback_target,
        ),
        StatementType.GOTO: lambda idx, stmt: _handle_goto_statement(
            graph,
            block,
            paragraph.paragraph_name,
            idx,
            stmt,
            paragraph_blocks,
        ),
    }

    control_encountered = False

    for index, statement in enumerate(paragraph.statements):
        handler = handlers.get(statement.statement_type)
        if handler is None:
            continue
        control_encountered = True
        handler(index, statement)

    if not control_encountered:
        graph.add_edge(
            CFGEdge(source=block, target=fallback_target, edge_type=CFGEdgeType.SEQUENTIAL)
        )


def _handle_if_statement(
    graph: ControlFlowGraph,
    block: BasicBlock,
    paragraph_name: str,
    index: int,
    statement: StatementNode,
    fallback_target: BasicBlock | ExitNode,
) -> None:
    node_id = f"if_{paragraph_name}_{index}"
    control_node = ControlFlowNode(
        node_id=node_id,
        control_type="IF",
        condition=statement.attributes.get("condition"),
        label=f"IF {paragraph_name}#{index}",
    )
    graph.add_node(control_node)
    graph.add_edge(CFGEdge(source=block, target=control_node, edge_type=CFGEdgeType.SEQUENTIAL))

    then_statements = statement.attributes.get("then_statements", [])
    then_block = BasicBlock(
        node_id=f"{paragraph_name}_if_then_{index}",
        label=f"{paragraph_name}-THEN-{index}",
        statements=then_statements,
    )
    graph.add_node(then_block)
    graph.add_edge(CFGEdge(source=control_node, target=then_block, edge_type=CFGEdgeType.TRUE))
    graph.add_edge(
        CFGEdge(source=then_block, target=fallback_target, edge_type=CFGEdgeType.SEQUENTIAL)
    )

    else_statements = statement.attributes.get("else_statements", [])
    if else_statements:
        else_block = BasicBlock(
            node_id=f"{paragraph_name}_if_else_{index}",
            label=f"{paragraph_name}-ELSE-{index}",
            statements=else_statements,
        )
        graph.add_node(else_block)
        graph.add_edge(CFGEdge(source=control_node, target=else_block, edge_type=CFGEdgeType.FALSE))
        graph.add_edge(
            CFGEdge(source=else_block, target=fallback_target, edge_type=CFGEdgeType.SEQUENTIAL)
        )
        return

    graph.add_edge(
        CFGEdge(source=control_node, target=fallback_target, edge_type=CFGEdgeType.FALSE)
    )


def _handle_perform_statement(
    graph: ControlFlowGraph,
    block: BasicBlock,
    paragraph_name: str,
    index: int,
    statement: StatementNode,
    paragraph_blocks: dict[str, BasicBlock],
    fallback_target: BasicBlock | ExitNode,
) -> None:
    target_name = statement.attributes.get("target_paragraph")
    control_node = ControlFlowNode(
        node_id=f"perform_{paragraph_name}_{index}",
        control_type="PERFORM",
        target_paragraph=target_name,
        label=f"PERFORM {target_name or 'UNKNOWN'}",
    )
    graph.add_node(control_node)
    graph.add_edge(CFGEdge(source=block, target=control_node, edge_type=CFGEdgeType.SEQUENTIAL))

    if not target_name:
        logger.warning("PERFORM statement without target paragraph in %s", paragraph_name)
        graph.add_edge(
            CFGEdge(source=control_node, target=fallback_target, edge_type=CFGEdgeType.SEQUENTIAL)
        )
        return

    target_block = paragraph_blocks.get(target_name)
    if target_block is None:
        logger.warning(
            "PERFORM target paragraph '%s' not found for paragraph '%s'.",
            target_name,
            paragraph_name,
        )
        graph.add_edge(
            CFGEdge(source=control_node, target=fallback_target, edge_type=CFGEdgeType.SEQUENTIAL)
        )
        return

    graph.add_edge(CFGEdge(source=control_node, target=target_block, edge_type=CFGEdgeType.CALL))
    graph.add_edge(
        CFGEdge(source=target_block, target=fallback_target, edge_type=CFGEdgeType.RETURN)
    )


def _handle_goto_statement(
    graph: ControlFlowGraph,
    block: BasicBlock,
    paragraph_name: str,
    index: int,
    statement: StatementNode,
    paragraph_blocks: dict[str, BasicBlock],
) -> None:
    target_name = statement.attributes.get("target_paragraph")
    control_node = ControlFlowNode(
        node_id=f"goto_{paragraph_name}_{index}",
        control_type="GOTO",
        target_paragraph=target_name,
        label=f"GOTO {target_name or 'UNKNOWN'}",
    )
    graph.add_node(control_node)
    graph.add_edge(CFGEdge(source=block, target=control_node, edge_type=CFGEdgeType.SEQUENTIAL))

    if not target_name:
        logger.warning("GOTO statement without target paragraph in %s", paragraph_name)
        return

    target_block = paragraph_blocks.get(target_name)
    if target_block is None:
        logger.warning(
            "GOTO target paragraph '%s' not found for paragraph '%s'.",
            target_name,
            paragraph_name,
        )
        return

    graph.add_edge(CFGEdge(source=control_node, target=target_block, edge_type=CFGEdgeType.GOTO))

"""Build Program Dependency Graphs (PDG) from COBOL AST, CFG, and DFG structures."""

from __future__ import annotations

import logging
from collections import defaultdict

from src.core.models.cobol_analysis_model import (
    BasicBlock,
    CFGEdgeType,
    ControlFlowGraph,
    ControlFlowNode,
    DataFlowGraph,
    DFGNode,
    DivisionNode,
    DivisionType,
    ParagraphNode,
    PDGEdge,
    PDGEdgeType,
    PDGNode,
    ProgramDependencyGraph,
    ProgramNode,
    SectionNode,
    StatementType,
    VariableDefNode,
)


logger = logging.getLogger(__name__)


class PDGBuilderError(ValueError):
    """Raised when the PDG cannot be constructed from the provided structures."""


def build_pdg(
    ast: ProgramNode, cfg: ControlFlowGraph, dfg: DataFlowGraph
) -> ProgramDependencyGraph:
    """Build a Program Dependency Graph from COBOL AST, CFG, and DFG.

    The PDG combines:
    - Control dependencies: derived from CFG (branching statements control execution)
    - Data dependencies: derived from DFG (variable definitions flow to uses)

    Args:
        ast: Program AST structure.
        cfg: Control Flow Graph.
        dfg: Data Flow Graph.

    Returns:
        ProgramDependencyGraph containing combined control and data dependencies.

    Raises:
        PDGBuilderError: If AST, CFG, or DFG arguments are invalid.
    """
    if not isinstance(ast, ProgramNode):
        raise PDGBuilderError("AST root must be a ProgramNode.")
    if not isinstance(cfg, ControlFlowGraph):
        raise PDGBuilderError("CFG must be a ControlFlowGraph instance.")
    if not isinstance(dfg, DataFlowGraph):
        raise PDGBuilderError("DFG must be a DataFlowGraph instance.")

    procedure_division = _find_procedure_division(ast.divisions)
    if procedure_division is None:
        raise PDGBuilderError("Procedure division is required to build PDG.")

    paragraphs = _collect_paragraphs(procedure_division.sections)
    if not paragraphs:
        raise PDGBuilderError("Procedure division must contain at least one paragraph.")

    graph = ProgramDependencyGraph()

    # Create PDG nodes for each statement
    pdg_nodes_map = _create_pdg_nodes(graph, cfg)

    # Add control dependency edges
    _add_control_dependencies(graph, cfg, pdg_nodes_map)

    # Add data dependency edges
    _add_data_dependencies(graph, dfg)

    return graph


def _find_procedure_division(divisions: list[DivisionNode]) -> DivisionNode | None:
    """Find the PROCEDURE division in the AST."""
    for division in divisions:
        if division.division_type == DivisionType.PROCEDURE:
            return division
    return None


def _collect_paragraphs(sections: list[SectionNode]) -> list[ParagraphNode]:
    """Collect all paragraphs from sections."""
    paragraphs: list[ParagraphNode] = []
    for section in sections:
        paragraphs.extend(section.paragraphs)
    return paragraphs


def _create_pdg_nodes(
    graph: ProgramDependencyGraph,
    cfg: ControlFlowGraph,
) -> dict[str, PDGNode]:
    """Create PDG nodes for each statement in the CFG.

    Returns:
        Dictionary mapping CFG node IDs to PDG nodes (can have multiple PDG nodes per CFG node).
    """
    pdg_nodes_map: dict[str, PDGNode] = {}
    statement_counter = 0

    # Create PDG nodes from all BasicBlock nodes in the CFG
    # This ensures we capture THEN/ELSE block statements as well
    for cfg_node in cfg.nodes:
        if isinstance(cfg_node, BasicBlock):
            for stmt_idx, statement in enumerate(cfg_node.statements):
                node_id = f"pdg_{cfg_node.node_id}_{stmt_idx}"
                statement_counter += 1

                # Create label based on statement type
                label = f"{statement.statement_type.name}"
                if statement.statement_type == StatementType.MOVE:
                    target = statement.attributes.get("target")
                    if target is not None and hasattr(target, "variable_name"):
                        label = f"MOVE -> {target.variable_name}"
                elif statement.statement_type == StatementType.IF:
                    label = "IF"
                elif statement.statement_type == StatementType.PERFORM:
                    target_para = statement.attributes.get("target_paragraph", "")
                    label = f"PERFORM {target_para}"

                pdg_node = PDGNode(
                    node_id=node_id,
                    statement=statement,
                    cfg_node_id=cfg_node.node_id,
                    location=statement.location,
                    label=label,
                )

                graph.add_node(pdg_node)
                pdg_nodes_map[node_id] = pdg_node

                # Also map by CFG node ID for control dependency creation
                # Note: This will map to the LAST statement in the block if there are multiple
                pdg_nodes_map[cfg_node.node_id] = pdg_node

        elif isinstance(cfg_node, ControlFlowNode):
            # Create PDG nodes for control flow nodes (branching points)
            node_id = f"pdg_{cfg_node.node_id}"
            statement_counter += 1

            pdg_node = PDGNode(
                node_id=node_id,
                statement=None,  # Control flow nodes don't have statements
                cfg_node_id=cfg_node.node_id,
                location=cfg_node.location,
                label=cfg_node.label,
            )

            graph.add_node(pdg_node)
            pdg_nodes_map[node_id] = pdg_node
            pdg_nodes_map[cfg_node.node_id] = pdg_node

    logger.info(f"Created {len(graph.nodes)} PDG nodes from CFG ({statement_counter} items)")
    return pdg_nodes_map


def _add_control_dependencies(
    graph: ProgramDependencyGraph,
    cfg: ControlFlowGraph,
    pdg_nodes_map: dict[str, PDGNode],
) -> None:
    """Add control dependency edges to the PDG.

    A node B is control-dependent on node A if:
    - A is a branching node (IF, PERFORM, etc.)
    - Whether B executes depends on the outcome of A
    """
    # Build a mapping of CFG node IDs to PDG nodes
    cfg_to_pdg_map: dict[str, list[PDGNode]] = defaultdict(list)
    for pdg_node in pdg_nodes_map.values():
        if pdg_node.cfg_node_id:
            cfg_to_pdg_map[pdg_node.cfg_node_id].append(pdg_node)

    # Find branching nodes and their control-dependent successors
    for cfg_node in cfg.nodes:
        if not isinstance(cfg_node, ControlFlowNode):
            continue

        # Get TRUE and FALSE branch targets
        true_edges = [
            e for e in cfg.edges if e.source == cfg_node and e.edge_type == CFGEdgeType.TRUE
        ]
        false_edges = [
            e for e in cfg.edges if e.source == cfg_node and e.edge_type == CFGEdgeType.FALSE
        ]

        # Create control dependency from branching node to branch targets
        branching_pdg_nodes = cfg_to_pdg_map.get(cfg_node.node_id, [])

        for true_edge in true_edges:
            target_pdg_nodes = cfg_to_pdg_map.get(true_edge.target.node_id, [])
            for branching_node in branching_pdg_nodes:
                for target_node in target_pdg_nodes:
                    edge = PDGEdge(
                        source=branching_node,
                        target=target_node,
                        edge_type=PDGEdgeType.CONTROL,
                        label="TRUE",
                    )
                    graph.add_edge(edge)

        for false_edge in false_edges:
            target_pdg_nodes = cfg_to_pdg_map.get(false_edge.target.node_id, [])
            for branching_node in branching_pdg_nodes:
                for target_node in target_pdg_nodes:
                    edge = PDGEdge(
                        source=branching_node,
                        target=target_node,
                        edge_type=PDGEdgeType.CONTROL,
                        label="FALSE",
                    )
                    graph.add_edge(edge)

    logger.info(
        f"Added {len([e for e in graph.edges if e.edge_type == PDGEdgeType.CONTROL])} control dependency edges"
    )


def _add_data_dependencies(
    graph: ProgramDependencyGraph,
    dfg: DataFlowGraph,
) -> None:
    """Add data dependency edges to the PDG.

    A node B is data-dependent on node A if:
    - A defines a variable V
    - B uses variable V
    - There's a def-use edge from A to B in the DFG
    """
    # Build mapping of DFG variable definition nodes to PDG nodes
    dfg_to_pdg_map: dict[str, PDGNode] = {}

    # Map DFG nodes to PDG nodes by matching statements
    for pdg_node in graph.nodes:
        if pdg_node.statement is None:
            continue

        # Find DFG nodes corresponding to this statement
        for dfg_node in dfg.nodes:
            if isinstance(dfg_node, VariableDefNode) and dfg_node.statement == pdg_node.statement:
                dfg_to_pdg_map[dfg_node.node_id] = pdg_node

    # Add data dependency edges based on DFG edges
    for dfg_edge in dfg.edges:
        source_pdg = dfg_to_pdg_map.get(dfg_edge.source.node_id)
        target_pdg = dfg_to_pdg_map.get(dfg_edge.target.node_id)

        if source_pdg and target_pdg and source_pdg != target_pdg:
            variable_name = (
                dfg_edge.source.variable_name if isinstance(dfg_edge.source, DFGNode) else None
            )

            edge = PDGEdge(
                source=source_pdg,
                target=target_pdg,
                edge_type=PDGEdgeType.DATA,
                label=variable_name or "",
                variable_name=variable_name,
            )
            graph.add_edge(edge)

    logger.info(
        f"Added {len([e for e in graph.edges if e.edge_type == PDGEdgeType.DATA])} data dependency edges"
    )

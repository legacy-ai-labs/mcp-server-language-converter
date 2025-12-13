"""Control Flow Graph (CFG) builder service for COBOL programs.

This module builds a Control Flow Graph from a COBOL AST (ParseNode).
The CFG represents all possible execution paths through the program and enables:
- Accurate cyclomatic complexity calculation
- Unreachable code detection
- Control flow analysis for migration planning

The CFG is built from the AST, not by re-parsing the source code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.core.services.cobol_analysis.cobol_parser_antlr_service import ParseNode


logger = logging.getLogger(__name__)


class CFGNodeType(str, Enum):
    """Types of nodes in the Control Flow Graph."""

    ENTRY = "ENTRY"
    EXIT = "EXIT"
    PARAGRAPH = "PARAGRAPH"
    SECTION = "SECTION"
    STATEMENT = "STATEMENT"
    DECISION = "DECISION"
    MERGE = "MERGE"
    CALL = "CALL"
    PERFORM = "PERFORM"
    GOTO = "GOTO"


class CFGEdgeType(str, Enum):
    """Types of edges in the Control Flow Graph."""

    SEQUENTIAL = "SEQUENTIAL"
    TRUE_BRANCH = "TRUE_BRANCH"
    FALSE_BRANCH = "FALSE_BRANCH"
    FALLTHROUGH = "FALLTHROUGH"
    GOTO = "GOTO"
    PERFORM = "PERFORM"
    RETURN = "RETURN"


class CFGNode(BaseModel):
    """A node in the Control Flow Graph."""

    id: str = Field(description="Unique node identifier")
    node_type: CFGNodeType = Field(description="Type of CFG node")
    label: str = Field(description="Human-readable label")
    ast_node_id: int | None = Field(default=None, description="Reference to AST node")
    line_number: int | None = Field(default=None, description="Source line number")
    statements: list[str] = Field(default_factory=list, description="Statements in this node")
    is_entry: bool = Field(default=False, description="Is program entry point")
    is_exit: bool = Field(default=False, description="Is program exit point")


class CFGEdge(BaseModel):
    """An edge in the Control Flow Graph."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    edge_type: CFGEdgeType = Field(description="Type of control flow")
    condition: str | None = Field(default=None, description="Branch condition if any")


class ControlFlowGraph(BaseModel):
    """Complete Control Flow Graph for a COBOL program."""

    program_name: str | None = Field(default=None, description="Program identifier")
    nodes: list[CFGNode] = Field(default_factory=list, description="CFG nodes")
    edges: list[CFGEdge] = Field(default_factory=list, description="CFG edges")
    entry_node: str | None = Field(default=None, description="Entry node ID")
    exit_nodes: list[str] = Field(default_factory=list, description="Exit node IDs")

    # Computed metrics
    cyclomatic_complexity: int = Field(default=1, description="Cyclomatic complexity (E - N + 2P)")
    node_count: int = Field(default=0, description="Total nodes")
    edge_count: int = Field(default=0, description="Total edges")
    unreachable_nodes: list[str] = Field(default_factory=list, description="Unreachable node IDs")
    paragraph_names: list[str] = Field(default_factory=list, description="All paragraph names")


@dataclass
class CFGBuilderContext:
    """Context for building the CFG."""

    node_counter: int = 0
    nodes: dict[str, CFGNode] = field(default_factory=dict)
    edges: list[CFGEdge] = field(default_factory=list)
    paragraph_nodes: dict[str, str] = field(default_factory=dict)  # name -> node_id
    current_node: str | None = None
    entry_node: str | None = None
    exit_nodes: list[str] = field(default_factory=list)

    def next_node_id(self) -> str:
        """Generate next unique node ID."""
        self.node_counter += 1
        return f"n{self.node_counter}"


class CFGBuilderError(Exception):
    """Exception raised when CFG building fails."""

    pass


def build_cfg_from_ast(
    ast: ParseNode | dict[str, Any],
    program_name: str | None = None,
) -> ControlFlowGraph:
    """Build a Control Flow Graph from a COBOL AST.

    Args:
        ast: ParseNode or dict representation of the AST
        program_name: Optional program name

    Returns:
        ControlFlowGraph with nodes, edges, and computed metrics

    Raises:
        CFGBuilderError: If CFG construction fails
    """
    try:
        # Convert dict to ParseNode if needed
        if isinstance(ast, dict):
            ast = _dict_to_parse_node(ast)

        ctx = CFGBuilderContext()

        # Create entry node
        entry_id = ctx.next_node_id()
        entry_node = CFGNode(
            id=entry_id,
            node_type=CFGNodeType.ENTRY,
            label="ENTRY",
            is_entry=True,
        )
        ctx.nodes[entry_id] = entry_node
        ctx.entry_node = entry_id
        ctx.current_node = entry_id

        # Find and process PROCEDURE DIVISION
        procedure_div = _find_node(ast, ["PROCEDURE_DIVISION", "ProcedureDivision"])
        if procedure_div:
            _process_procedure_division(procedure_div, ctx)
        else:
            logger.warning("No PROCEDURE DIVISION found in AST")

        # Create exit node if not already created
        if not ctx.exit_nodes:
            exit_id = ctx.next_node_id()
            exit_node = CFGNode(
                id=exit_id,
                node_type=CFGNodeType.EXIT,
                label="EXIT",
                is_exit=True,
            )
            ctx.nodes[exit_id] = exit_node
            ctx.exit_nodes.append(exit_id)

            # Connect last node to exit
            if ctx.current_node and ctx.current_node != exit_id:
                ctx.edges.append(
                    CFGEdge(
                        source=ctx.current_node,
                        target=exit_id,
                        edge_type=CFGEdgeType.SEQUENTIAL,
                    )
                )

        # Build the CFG
        cfg = ControlFlowGraph(
            program_name=program_name,
            nodes=list(ctx.nodes.values()),
            edges=ctx.edges,
            entry_node=ctx.entry_node,
            exit_nodes=ctx.exit_nodes,
            node_count=len(ctx.nodes),
            edge_count=len(ctx.edges),
            paragraph_names=list(ctx.paragraph_nodes.keys()),
        )

        # Compute metrics
        _compute_cfg_metrics(cfg)

        logger.info(
            f"Built CFG: {cfg.node_count} nodes, {cfg.edge_count} edges, "
            f"cyclomatic complexity={cfg.cyclomatic_complexity}"
        )

        return cfg

    except Exception as e:
        logger.exception("Failed to build CFG")
        raise CFGBuilderError(f"CFG construction failed: {e}") from e


def _dict_to_parse_node(node_dict: dict[str, Any]) -> ParseNode:
    """Convert dictionary to ParseNode."""
    children = [
        _dict_to_parse_node(child)
        for child in node_dict.get("children", [])
        if isinstance(child, dict)
    ]

    return ParseNode(
        type=node_dict.get("type", "Unknown"),
        children=children,
        value=node_dict.get("value"),
        start_line=node_dict.get("start_line"),
        start_column=node_dict.get("start_column"),
        end_line=node_dict.get("end_line"),
        end_column=node_dict.get("end_column"),
        id=node_dict.get("id"),
        rule_name=node_dict.get("rule_name"),
        text=node_dict.get("text"),
    )


def _find_node(node: ParseNode, type_names: list[str]) -> ParseNode | None:
    """Find a node by type name (case-insensitive search)."""
    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        return node

    for child in node.children:
        result = _find_node(child, type_names)
        if result:
            return result

    return None


def _find_all_nodes(node: ParseNode, type_names: list[str]) -> list[ParseNode]:
    """Find all nodes matching type names."""
    results: list[ParseNode] = []

    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        results.append(node)

    for child in node.children:
        results.extend(_find_all_nodes(child, type_names))

    return results


def _process_procedure_division(proc_div: ParseNode, ctx: CFGBuilderContext) -> None:
    """Process PROCEDURE DIVISION to build CFG."""
    # Find all paragraphs
    paragraphs = _find_all_nodes(proc_div, ["Paragraph", "paragraph", "PARAGRAPH_NAME"])
    # Note: sections could be processed for more detailed CFG in future

    # First pass: create nodes for all paragraphs
    for para in paragraphs:
        para_name = _extract_name(para)
        if para_name:
            node_id = ctx.next_node_id()
            para_node = CFGNode(
                id=node_id,
                node_type=CFGNodeType.PARAGRAPH,
                label=para_name,
                ast_node_id=para.id,
                line_number=para.start_line,
            )
            ctx.nodes[node_id] = para_node
            ctx.paragraph_nodes[para_name] = node_id

    # Connect entry to first paragraph
    if ctx.paragraph_nodes:
        first_para = next(iter(ctx.paragraph_nodes.values()))
        ctx.edges.append(
            CFGEdge(
                source=ctx.entry_node or "",
                target=first_para,
                edge_type=CFGEdgeType.SEQUENTIAL,
            )
        )
        ctx.current_node = first_para

    # Second pass: process statements within paragraphs
    for para in paragraphs:
        para_name = _extract_name(para)
        if para_name and para_name in ctx.paragraph_nodes:
            _process_paragraph_statements(para, ctx, ctx.paragraph_nodes[para_name])

    # Connect sequential paragraphs
    para_list = list(ctx.paragraph_nodes.values())
    for i in range(len(para_list) - 1):
        # Check if there's already an edge from this paragraph
        has_outgoing = any(e.source == para_list[i] for e in ctx.edges)
        if not has_outgoing:
            ctx.edges.append(
                CFGEdge(
                    source=para_list[i],
                    target=para_list[i + 1],
                    edge_type=CFGEdgeType.FALLTHROUGH,
                )
            )


def _process_paragraph_statements(
    para: ParseNode, ctx: CFGBuilderContext, para_node_id: str
) -> None:
    """Process statements within a paragraph."""
    # Find statements in this paragraph
    statements = _find_all_nodes(
        para,
        [
            "Statement",
            "statement",
            "IfStatement",
            "ifStatement",
            "EvaluateStatement",
            "evaluateStatement",
            "PerformStatement",
            "performStatement",
            "GoToStatement",
            "gotoStatement",
            "GobackStatement",
            "gobackStatement",
            "StopStatement",
            "stopStatement",
            "CallStatement",
            "callStatement",
        ],
    )

    current = para_node_id

    for stmt in statements:
        stmt_type = stmt.type.upper() if stmt.type else ""

        if "IF" in stmt_type:
            current = _process_if_statement(stmt, ctx, current)
        elif "EVALUATE" in stmt_type:
            current = _process_evaluate_statement(stmt, ctx, current)
        elif "PERFORM" in stmt_type:
            _process_perform_statement(stmt, ctx, current)
        elif "GOTO" in stmt_type:
            _process_goto_statement(stmt, ctx, current)
        elif "GOBACK" in stmt_type or "STOP" in stmt_type:
            _process_exit_statement(stmt, ctx, current)
        elif "CALL" in stmt_type:
            _process_call_statement(stmt, ctx, current)


def _process_if_statement(stmt: ParseNode, ctx: CFGBuilderContext, current: str) -> str:
    """Process IF statement and return the merge node."""
    # Create decision node
    decision_id = ctx.next_node_id()
    decision_node = CFGNode(
        id=decision_id,
        node_type=CFGNodeType.DECISION,
        label="IF",
        ast_node_id=stmt.id,
        line_number=stmt.start_line,
    )
    ctx.nodes[decision_id] = decision_node

    # Connect from current
    ctx.edges.append(
        CFGEdge(
            source=current,
            target=decision_id,
            edge_type=CFGEdgeType.SEQUENTIAL,
        )
    )

    # Create merge node
    merge_id = ctx.next_node_id()
    merge_node = CFGNode(
        id=merge_id,
        node_type=CFGNodeType.MERGE,
        label="END-IF",
        ast_node_id=stmt.id,
    )
    ctx.nodes[merge_id] = merge_node

    # True branch
    true_id = ctx.next_node_id()
    true_node = CFGNode(
        id=true_id,
        node_type=CFGNodeType.STATEMENT,
        label="THEN",
    )
    ctx.nodes[true_id] = true_node

    ctx.edges.append(
        CFGEdge(
            source=decision_id,
            target=true_id,
            edge_type=CFGEdgeType.TRUE_BRANCH,
            condition="TRUE",
        )
    )
    ctx.edges.append(
        CFGEdge(
            source=true_id,
            target=merge_id,
            edge_type=CFGEdgeType.SEQUENTIAL,
        )
    )

    # Check for ELSE
    has_else = any(child.type and "ELSE" in child.type.upper() for child in stmt.children)

    if has_else:
        false_id = ctx.next_node_id()
        false_node = CFGNode(
            id=false_id,
            node_type=CFGNodeType.STATEMENT,
            label="ELSE",
        )
        ctx.nodes[false_id] = false_node

        ctx.edges.append(
            CFGEdge(
                source=decision_id,
                target=false_id,
                edge_type=CFGEdgeType.FALSE_BRANCH,
                condition="FALSE",
            )
        )
        ctx.edges.append(
            CFGEdge(
                source=false_id,
                target=merge_id,
                edge_type=CFGEdgeType.SEQUENTIAL,
            )
        )
    else:
        # No ELSE - connect directly to merge
        ctx.edges.append(
            CFGEdge(
                source=decision_id,
                target=merge_id,
                edge_type=CFGEdgeType.FALSE_BRANCH,
                condition="FALSE",
            )
        )

    return merge_id


def _process_evaluate_statement(stmt: ParseNode, ctx: CFGBuilderContext, current: str) -> str:
    """Process EVALUATE statement and return the merge node."""
    # Create decision node
    decision_id = ctx.next_node_id()
    decision_node = CFGNode(
        id=decision_id,
        node_type=CFGNodeType.DECISION,
        label="EVALUATE",
        ast_node_id=stmt.id,
        line_number=stmt.start_line,
    )
    ctx.nodes[decision_id] = decision_node

    ctx.edges.append(
        CFGEdge(
            source=current,
            target=decision_id,
            edge_type=CFGEdgeType.SEQUENTIAL,
        )
    )

    # Create merge node
    merge_id = ctx.next_node_id()
    merge_node = CFGNode(
        id=merge_id,
        node_type=CFGNodeType.MERGE,
        label="END-EVALUATE",
    )
    ctx.nodes[merge_id] = merge_node

    # Find WHEN clauses
    when_clauses = _find_all_nodes(stmt, ["WhenPhrase", "whenPhrase", "When"])
    when_count = max(len(when_clauses), 1)  # At least one branch

    for i in range(when_count):
        when_id = ctx.next_node_id()
        when_node = CFGNode(
            id=when_id,
            node_type=CFGNodeType.STATEMENT,
            label=f"WHEN_{i + 1}",
        )
        ctx.nodes[when_id] = when_node

        ctx.edges.append(
            CFGEdge(
                source=decision_id,
                target=when_id,
                edge_type=CFGEdgeType.TRUE_BRANCH,
                condition=f"WHEN_{i + 1}",
            )
        )
        ctx.edges.append(
            CFGEdge(
                source=when_id,
                target=merge_id,
                edge_type=CFGEdgeType.SEQUENTIAL,
            )
        )

    return merge_id


def _process_perform_statement(stmt: ParseNode, ctx: CFGBuilderContext, current: str) -> None:
    """Process PERFORM statement."""
    # Extract target paragraph name
    target_name = _extract_perform_target(stmt)

    if target_name and target_name in ctx.paragraph_nodes:
        target_id = ctx.paragraph_nodes[target_name]

        # Create PERFORM edge
        ctx.edges.append(
            CFGEdge(
                source=current,
                target=target_id,
                edge_type=CFGEdgeType.PERFORM,
            )
        )

        # Create return edge
        ctx.edges.append(
            CFGEdge(
                source=target_id,
                target=current,
                edge_type=CFGEdgeType.RETURN,
            )
        )


def _process_goto_statement(stmt: ParseNode, ctx: CFGBuilderContext, current: str) -> None:
    """Process GO TO statement."""
    target_name = _extract_goto_target(stmt)

    if target_name and target_name in ctx.paragraph_nodes:
        target_id = ctx.paragraph_nodes[target_name]

        ctx.edges.append(
            CFGEdge(
                source=current,
                target=target_id,
                edge_type=CFGEdgeType.GOTO,
            )
        )


def _process_exit_statement(_stmt: ParseNode, ctx: CFGBuilderContext, current: str) -> None:
    """Process GOBACK/STOP RUN statement."""
    # Note: _stmt could be used to extract exit type (GOBACK vs STOP RUN) if needed
    # Create or reuse exit node
    if not ctx.exit_nodes:
        exit_id = ctx.next_node_id()
        exit_node = CFGNode(
            id=exit_id,
            node_type=CFGNodeType.EXIT,
            label="EXIT",
            is_exit=True,
        )
        ctx.nodes[exit_id] = exit_node
        ctx.exit_nodes.append(exit_id)

    ctx.edges.append(
        CFGEdge(
            source=current,
            target=ctx.exit_nodes[0],
            edge_type=CFGEdgeType.SEQUENTIAL,
        )
    )


def _process_call_statement(stmt: ParseNode, ctx: CFGBuilderContext, current: str) -> None:
    """Process CALL statement."""
    call_id = ctx.next_node_id()
    target_name = _extract_call_target(stmt) or "EXTERNAL"

    call_node = CFGNode(
        id=call_id,
        node_type=CFGNodeType.CALL,
        label=f"CALL {target_name}",
        ast_node_id=stmt.id,
        line_number=stmt.start_line,
    )
    ctx.nodes[call_id] = call_node

    ctx.edges.append(
        CFGEdge(
            source=current,
            target=call_id,
            edge_type=CFGEdgeType.SEQUENTIAL,
        )
    )


def _extract_name(node: ParseNode) -> str | None:
    """Extract name from a paragraph or section node."""
    # Check for value attribute
    if node.value:
        return str(node.value)

    # Search children for name
    for child in node.children:
        if child.type and "Name" in child.type:
            if child.value:
                return str(child.value)
            if child.text:
                return child.text
        # Recurse into children
        name = _extract_name(child)
        if name:
            return name

    return None


def _extract_perform_target(stmt: ParseNode) -> str | None:
    """Extract target paragraph name from PERFORM statement."""
    # Look for procedureName or paragraphName
    for child in stmt.children:
        if child.type and ("procedureName" in child.type or "paragraphName" in child.type):
            return _extract_name(child)
        # Check for identifier
        if child.type and "Identifier" in child.type:
            if child.value:
                return str(child.value)
            if child.text:
                return child.text

    return None


def _extract_goto_target(stmt: ParseNode) -> str | None:
    """Extract target from GO TO statement."""
    return _extract_perform_target(stmt)  # Same logic


def _extract_call_target(stmt: ParseNode) -> str | None:
    """Extract target program from CALL statement."""
    for child in stmt.children:
        if child.type and "Literal" in child.type and child.text:
            return child.text.strip("'\"")
        if child.type and "Identifier" in child.type and child.value:
            return str(child.value)

    return None


def _compute_cfg_metrics(cfg: ControlFlowGraph) -> None:
    """Compute CFG metrics including cyclomatic complexity."""
    # Cyclomatic complexity: M = E - N + 2P
    # E = edges, N = nodes, P = connected components (usually 1)
    e = len(cfg.edges)
    n = len(cfg.nodes)
    p = 1  # Assume single connected component

    cfg.cyclomatic_complexity = e - n + 2 * p

    # Ensure minimum complexity of 1
    cfg.cyclomatic_complexity = max(cfg.cyclomatic_complexity, 1)

    # Find unreachable nodes using BFS from entry
    reachable: set[str] = set()
    if cfg.entry_node:
        queue = [cfg.entry_node]
        while queue:
            node_id = queue.pop(0)
            if node_id in reachable:
                continue
            reachable.add(node_id)

            # Find outgoing edges
            for edge in cfg.edges:
                if edge.source == node_id and edge.target not in reachable:
                    queue.append(edge.target)

    # Mark unreachable nodes
    all_nodes = {node.id for node in cfg.nodes}
    cfg.unreachable_nodes = list(all_nodes - reachable)


def serialize_cfg(cfg: ControlFlowGraph) -> dict[str, Any]:
    """Serialize CFG to dictionary for JSON output."""
    return cfg.model_dump(mode="json")

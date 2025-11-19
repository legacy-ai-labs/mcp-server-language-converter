"""Regenerate all JSON files (AST, CFG, DFG) with fixed implementations."""

import json
import sys
from typing import Any


sys.path.insert(0, "src")

from src.core.models.cobol_analysis_model import (
    BasicBlock,
    CFGEdge,
    ControlFlowNode,
    DFGEdge,
    DivisionNode,
    EntryNode,
    ExitNode,
    ExpressionNode,
    LiteralNode,
    ParagraphNode,
    ProgramNode,
    SectionNode,
    StatementNode,
    VariableDefNode,
    VariableNode,
    VariableUseNode,
)
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.cobol_parser_antlr_service import parse_cobol
from src.core.services.dfg_builder_service import build_dfg


# ============================================================================
# AST Serialization
# ============================================================================


def serialize_ast(ast: ProgramNode) -> dict[str, Any]:
    """Serialize AST to JSON."""
    return {
        "success": True,
        "ast": serialize_program_node(ast),
        "program_name": ast.program_name,
    }


def serialize_program_node(node: ProgramNode) -> dict[str, Any]:
    """Serialize ProgramNode."""
    return {
        "type": "ProgramNode",
        "program_name": node.program_name,
        "divisions": [serialize_division_node(d) for d in node.divisions],
        "location": node.location,
    }


def serialize_division_node(node: DivisionNode) -> dict[str, Any]:
    """Serialize DivisionNode."""
    return {
        "type": "DivisionNode",
        "division_type": node.division_type.name,
        "sections": [serialize_section_node(s) for s in node.sections],
        "location": node.location,
    }


def serialize_section_node(node: SectionNode) -> dict[str, Any]:
    """Serialize SectionNode."""
    return {
        "type": "SectionNode",
        "section_name": node.section_name,
        "paragraphs": [serialize_paragraph_node(p) for p in node.paragraphs],
        "location": node.location,
    }


def serialize_paragraph_node(node: ParagraphNode) -> dict[str, Any]:
    """Serialize ParagraphNode."""
    return {
        "type": "ParagraphNode",
        "paragraph_name": node.paragraph_name,
        "statements": [serialize_statement_node(s) for s in node.statements],
        "location": node.location,
    }


def serialize_statement_node(node: StatementNode) -> dict[str, Any]:
    """Serialize StatementNode."""
    # Serialize attributes
    attrs = {}
    for key, value in node.attributes.items():
        if isinstance(value, VariableNode):
            attrs[key] = serialize_variable_node(value)
        elif isinstance(value, LiteralNode):
            attrs[key] = serialize_literal_node(value)
        elif isinstance(value, ExpressionNode):
            attrs[key] = serialize_expression_node(value)
        elif isinstance(value, list):
            attrs[key] = [
                serialize_statement_node(item)
                if isinstance(item, StatementNode)
                else serialize_dict(item)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            attrs[key] = value

    return {
        "type": "StatementNode",
        "statement_type": node.statement_type.name,
        "attributes": attrs,
        "location": node.location,
    }


def serialize_variable_node(node: VariableNode) -> dict[str, Any]:
    """Serialize VariableNode."""
    return {
        "type": "VariableNode",
        "variable_name": node.variable_name,
        "pic_clause": node.pic_clause,
        "level_number": node.level_number,
        "location": node.location,
    }


def serialize_literal_node(node: LiteralNode) -> dict[str, Any]:
    """Serialize LiteralNode."""
    return {
        "type": "LiteralNode",
        "value": node.value,
        "literal_type": node.literal_type,
        "location": node.location,
        "children": [],
    }


def serialize_expression_node(node: ExpressionNode) -> dict[str, Any]:
    """Serialize ExpressionNode."""
    return {
        "type": "ExpressionNode",
        "operator": node.operator,
        "left": serialize_variable_node(node.left)
        if isinstance(node.left, VariableNode)
        else node.left,
        "right": serialize_variable_node(node.right)
        if isinstance(node.right, VariableNode)
        else node.right,
        "value": node.value,
        "location": node.location,
    }


def serialize_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Serialize dict with special handling for model objects."""
    result = {}
    for key, value in d.items():
        if isinstance(value, LiteralNode):
            result[key] = serialize_literal_node(value)
        elif isinstance(value, VariableNode):
            result[key] = serialize_variable_node(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_statement_node(item) if isinstance(item, StatementNode) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


# ============================================================================
# CFG Serialization
# ============================================================================


def serialize_cfg(cfg) -> dict[str, Any]:
    """Serialize ControlFlowGraph to JSON."""
    nodes = []
    for node in cfg.nodes:
        if isinstance(node, EntryNode):
            nodes.append(serialize_entry_node(node))
        elif isinstance(node, ExitNode):
            nodes.append(serialize_exit_node(node))
        elif isinstance(node, BasicBlock):
            nodes.append(serialize_basic_block(node))
        elif isinstance(node, ControlFlowNode):
            nodes.append(serialize_control_flow_node(node))
        else:
            nodes.append({"node_type": type(node).__name__, "node_id": node.node_id})

    edges = [serialize_cfg_edge(edge) for edge in cfg.edges]

    return {
        "entry_node": serialize_entry_node(cfg.entry_node),
        "exit_node": serialize_exit_node(cfg.exit_node),
        "nodes": nodes,
        "edges": edges,
    }


def serialize_entry_node(node: EntryNode) -> dict[str, Any]:
    """Serialize EntryNode."""
    return {
        "node_id": node.node_id,
        "label": node.label,
        "location": node.location,
        "node_type": "EntryNode",
    }


def serialize_exit_node(node: ExitNode) -> dict[str, Any]:
    """Serialize ExitNode."""
    return {
        "node_id": node.node_id,
        "label": node.label,
        "location": node.location,
        "node_type": "ExitNode",
    }


def serialize_basic_block(node: BasicBlock) -> dict[str, Any]:
    """Serialize BasicBlock."""
    return {
        "node_id": node.node_id,
        "label": node.label,
        "location": node.location,
        "statements": [serialize_statement_node(s) for s in node.statements],
        "node_type": "BasicBlock",
    }


def serialize_control_flow_node(node: ControlFlowNode) -> dict[str, Any]:
    """Serialize ControlFlowNode."""
    result = {
        "node_id": node.node_id,
        "label": node.label,
        "location": node.location,
        "control_type": node.control_type,
        "condition": serialize_expression_node(node.condition) if node.condition else None,
        "target_paragraph": node.target_paragraph,
        "node_type": "ControlFlowNode",
    }
    return result


def serialize_cfg_edge(edge: CFGEdge) -> dict[str, Any]:
    """Serialize CFGEdge."""
    return {
        "source_id": edge.source.node_id if edge.source else None,
        "target_id": edge.target.node_id if edge.target else None,
        "edge_type": edge.edge_type.name if edge.edge_type else None,
        "label": edge.label,
    }


# ============================================================================
# DFG Serialization
# ============================================================================


def serialize_dfg(dfg) -> dict[str, Any]:
    """Serialize DataFlowGraph to JSON."""
    nodes = []
    for node in dfg.nodes:
        if isinstance(node, VariableDefNode):
            nodes.append(serialize_variable_def_node(node))
        elif isinstance(node, VariableUseNode):
            nodes.append(serialize_variable_use_node(node))
        else:
            nodes.append(
                {
                    "node_type": type(node).__name__,
                    "node_id": node.node_id if hasattr(node, "node_id") else "unknown",
                }
            )

    edges = [serialize_dfg_edge(edge) for edge in dfg.edges]

    return {
        "nodes": nodes,
        "edges": edges,
    }


def serialize_variable_def_node(node: VariableDefNode) -> dict[str, Any]:
    """Serialize VariableDefNode to JSON."""
    result = {
        "node_type": "VariableDefNode",
        "node_id": node.node_id,
        "variable_name": node.variable_name,
        "location": node.location,
    }

    if hasattr(node, "statement") and node.statement:
        result["statement_type"] = (
            str(node.statement.statement_type)
            if hasattr(node.statement, "statement_type")
            else None
        )

    return result


def serialize_variable_use_node(node: VariableUseNode) -> dict[str, Any]:
    """Serialize VariableUseNode to JSON."""
    return {
        "node_type": "VariableUseNode",
        "node_id": node.node_id,
        "variable_name": node.variable_name,
        "location": node.location,
    }


def serialize_dfg_edge(edge: DFGEdge) -> dict[str, Any]:
    """Serialize DFGEdge to JSON."""
    return {
        "source_id": edge.source.node_id if edge.source else None,
        "target_id": edge.target.node_id if edge.target else None,
        "edge_type": edge.edge_type.name if edge.edge_type else None,
    }


# ============================================================================
# Main
# ============================================================================


def main():
    """Regenerate all JSON files."""
    print("=" * 80)
    print("REGENERATING ALL JSON FILES")
    print("=" * 80)
    print()

    cobol_file = "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"

    # Read COBOL file
    print("1. Reading COBOL file...")
    with open(cobol_file) as f:
        cobol_code = f.read()
    print(f"   ✓ Read {len(cobol_code)} characters from {cobol_file}")
    print()

    # Parse COBOL
    print("2. Parsing COBOL...")
    parsed = parse_cobol(cobol_code)
    print(f"   ✓ Parsed: {parsed.node_type}")
    print()

    # Build AST
    print("3. Building AST...")
    ast = build_ast(parsed)
    print(f"   ✓ AST: {ast.program_name}")
    print()

    # Save AST
    print("4. Saving AST to JSON...")
    ast_data = serialize_ast(ast)
    ast_file = "tests/cobol_samples/ast.json"
    with open(ast_file, "w") as f:
        json.dump(ast_data, f, indent=2)
    print(f"   ✓ Saved to {ast_file}")
    print()

    # Build CFG
    print("5. Building CFG...")
    cfg = build_cfg(ast)
    print(f"   ✓ CFG: {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")
    print()

    # Check PERFORM edges
    print("6. Checking PERFORM edges...")
    perform_edges = [e for e in cfg.edges if "perform" in e.source.node_id]
    for edge in perform_edges:
        print(f"   - {edge.source.label} -> {edge.target.label}")
    print()

    # Save CFG
    print("7. Saving CFG to JSON...")
    cfg_data = serialize_cfg(cfg)
    cfg_file = "tests/cobol_samples/cfg.json"
    with open(cfg_file, "w") as f:
        json.dump(cfg_data, f, indent=2)
    print(f"   ✓ Saved to {cfg_file}")
    print()

    # Build DFG
    print("8. Building DFG...")
    dfg = build_dfg(ast, cfg)
    print(f"   ✓ DFG: {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")
    print()

    # Check DFG edges for LS-VALIDATION-CODE
    print("9. Checking DFG edges for LS-VALIDATION-CODE...")
    ls_val_edges = [
        e
        for e in dfg.edges
        if hasattr(e.source, "variable_name") and "LS-VALIDATION-CODE" in e.source.variable_name
    ]
    for edge in ls_val_edges:
        print(f"   - {edge.source.node_id} -> {edge.target.node_id}")

    # Check for incorrect edge between branches
    has_error = False
    for edge in dfg.edges:
        if hasattr(edge.source, "node_id") and hasattr(edge.target, "node_id"):
            if (
                edge.source.node_id.endswith("_0")
                and edge.target.node_id.endswith("_1")
                and "LS-VALIDATION-CODE" in edge.source.node_id
                and "LS-VALIDATION-CODE" in edge.target.node_id
            ):
                print(
                    f"   ❌ ERROR: Edge between THEN and ELSE: {edge.source.node_id} -> {edge.target.node_id}"
                )
                has_error = True

    if not has_error:
        print("   ✓ No incorrect edges between IF branches")
    print()

    # Save DFG
    print("10. Saving DFG to JSON...")
    dfg_data = serialize_dfg(dfg)
    dfg_file = "tests/cobol_samples/dfg.json"
    with open(dfg_file, "w") as f:
        json.dump(dfg_data, f, indent=2)
    print(f"    ✓ Saved to {dfg_file}")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"AST: {ast_file}")
    print(f"  - Divisions: {len(ast.divisions)}")
    print()
    print(f"CFG: {cfg_file}")
    print(f"  - Nodes: {len(cfg.nodes)}")
    print(f"  - Edges: {len(cfg.edges)}")
    print(f"  - PERFORM edges: {len(perform_edges)}")
    print()
    print(f"DFG: {dfg_file}")
    print(f"  - Nodes: {len(dfg.nodes)}")
    print(f"  - Edges: {len(dfg.edges)}")
    print()
    print("✅ All JSON files successfully regenerated!")
    print("=" * 80)


if __name__ == "__main__":
    main()

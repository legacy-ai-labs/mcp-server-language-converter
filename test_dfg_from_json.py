"""Test DFG builder using serialized AST and CFG JSON files.

This script loads pre-computed AST and CFG from JSON files and
tests the DFG building process.
"""

import json
import sys
from typing import Any


sys.path.insert(0, "src")

from src.core.models.cobol_analysis_model import (
    BasicBlock,
    CFGEdge,
    CFGEdgeType,
    CFGNode,
    ControlFlowGraph,
    ControlFlowNode,
    DivisionNode,
    DivisionType,
    EntryNode,
    ExitNode,
    ExpressionNode,
    LiteralNode,
    ParagraphNode,
    ProgramNode,
    SectionNode,
    StatementNode,
    StatementType,
    VariableNode,
)
from src.core.services.dfg_builder_service import build_dfg


def deserialize_variable_node(data: dict[str, Any]) -> VariableNode:
    """Deserialize VariableNode from JSON."""
    return VariableNode(
        variable_name=data.get("variable_name", ""),
        pic_clause=data.get("pic_clause"),
        level_number=data.get("level_number"),
        location=data.get("location"),
    )


def deserialize_literal_node(data: dict[str, Any]) -> LiteralNode:
    """Deserialize LiteralNode from JSON."""
    return LiteralNode(
        value=data.get("value"),
        literal_type=data.get("literal_type", "STRING"),
        location=data.get("location"),
    )


def deserialize_expression_node(data: dict[str, Any] | None) -> ExpressionNode | None:
    """Deserialize ExpressionNode from JSON."""
    if not data:
        return None

    return ExpressionNode(
        operator=data.get("operator"),
        left=data.get("left"),
        right=data.get("right"),
        value=data.get("value"),
        location=data.get("location"),
    )


def deserialize_statement_node(data: dict[str, Any]) -> StatementNode:
    """Deserialize StatementNode from JSON."""
    stmt_type_str = data.get("statement_type", "")

    # Convert string to StatementType enum
    try:
        stmt_type = StatementType[stmt_type_str]
    except KeyError:
        print(f"Warning: Unknown statement type '{stmt_type_str}', using DISPLAY")
        stmt_type = StatementType.DISPLAY

    # Process attributes
    attributes = data.get("attributes", {})
    processed_attrs = {}

    for key, value in attributes.items():
        if isinstance(value, dict):
            if value.get("type") == "VariableNode":
                processed_attrs[key] = deserialize_variable_node(value)
            elif value.get("type") == "LiteralNode":
                processed_attrs[key] = deserialize_literal_node(value)
            elif value.get("type") == "ExpressionNode":
                processed_attrs[key] = deserialize_expression_node(value)
            else:
                processed_attrs[key] = value
        elif isinstance(value, list):
            # Handle lists (like then_statements, else_statements)
            processed_attrs[key] = [
                deserialize_statement_node(item)
                if isinstance(item, dict) and item.get("type") == "StatementNode"
                else item
                for item in value
            ]
        else:
            processed_attrs[key] = value

    return StatementNode(
        statement_type=stmt_type,
        attributes=processed_attrs,
        location=data.get("location"),
    )


def deserialize_paragraph_node(data: dict[str, Any]) -> ParagraphNode:
    """Deserialize ParagraphNode from JSON."""
    statements = [deserialize_statement_node(stmt) for stmt in data.get("statements", [])]

    paragraph = ParagraphNode(
        paragraph_name=data.get("paragraph_name", ""),
        statements=statements,
        location=data.get("location"),
    )
    paragraph.children = list(statements)
    return paragraph


def deserialize_section_node(data: dict[str, Any]) -> SectionNode:
    """Deserialize SectionNode from JSON."""
    paragraphs = [deserialize_paragraph_node(para) for para in data.get("paragraphs", [])]

    section = SectionNode(
        section_name=data.get("section_name", ""),
        paragraphs=paragraphs,
        location=data.get("location"),
    )
    section.children = list(paragraphs)
    return section


def deserialize_division_node(data: dict[str, Any]) -> DivisionNode:
    """Deserialize DivisionNode from JSON."""
    div_type_str = data.get("division_type", "")

    # Convert string to DivisionType enum
    try:
        div_type = DivisionType[div_type_str]
    except KeyError:
        print(f"Warning: Unknown division type '{div_type_str}', using IDENTIFICATION")
        div_type = DivisionType.IDENTIFICATION

    sections = [deserialize_section_node(sect) for sect in data.get("sections", [])]

    division = DivisionNode(
        division_type=div_type,
        sections=sections,
        location=data.get("location"),
    )
    division.children = list(sections)
    return division


def deserialize_program_node(data: dict[str, Any]) -> ProgramNode:
    """Deserialize ProgramNode from JSON."""
    divisions = [deserialize_division_node(div) for div in data.get("divisions", [])]

    program = ProgramNode(
        program_name=data.get("program_name", "UNKNOWN"),
        divisions=divisions,
        location=data.get("location"),
    )
    program.children = list(divisions)
    return program


def deserialize_cfg_node(data: dict[str, Any]) -> CFGNode:
    """Deserialize a CFG node from JSON."""
    node_type = data.get("node_type")

    if node_type == "EntryNode":
        return EntryNode(
            node_id=data.get("node_id", "entry"),
            location=data.get("location"),
        )
    elif node_type == "ExitNode":
        return ExitNode(
            node_id=data.get("node_id", "exit"),
            location=data.get("location"),
        )
    elif node_type == "BasicBlock":
        statements = [deserialize_statement_node(stmt) for stmt in data.get("statements", [])]
        return BasicBlock(
            node_id=data.get("node_id", ""),
            statements=statements,
            location=data.get("location"),
        )
    elif node_type == "ControlFlowNode":
        return ControlFlowNode(
            node_id=data.get("node_id", ""),
            control_type=data.get("control_type"),
            condition=deserialize_expression_node(data.get("condition")),
            target_paragraph=data.get("target_paragraph"),
            location=data.get("location"),
        )
    else:
        # Default to BasicBlock
        return BasicBlock(
            node_id=data.get("node_id", ""),
            statements=[],
            location=data.get("location"),
        )


def deserialize_control_flow_graph(data: dict[str, Any]) -> ControlFlowGraph:
    """Deserialize ControlFlowGraph from JSON."""
    # Deserialize nodes
    nodes = [deserialize_cfg_node(node_data) for node_data in data.get("nodes", [])]

    # Create node lookup by ID
    node_by_id = {node.node_id: node for node in nodes}

    # Deserialize edges
    edges = []
    for edge_data in data.get("edges", []):
        source_id = edge_data.get("source_id", "")
        target_id = edge_data.get("target_id", "")
        edge_type_str = edge_data.get("edge_type", "SEQUENTIAL")

        # Look up source and target nodes
        source_node = node_by_id.get(source_id)
        target_node = node_by_id.get(target_id)

        if source_node and target_node:
            try:
                edge_type = CFGEdgeType[edge_type_str]
            except KeyError:
                edge_type = CFGEdgeType.SEQUENTIAL

            edge = CFGEdge(
                source=source_node,
                target=target_node,
                edge_type=edge_type,
                label=edge_data.get("label", ""),
            )
            edges.append(edge)
        else:
            print(f"Warning: Could not find nodes for edge {source_id} → {target_id}")

    # Find entry and exit nodes
    entry_node = next((n for n in nodes if isinstance(n, EntryNode)), None)
    exit_node = next((n for n in nodes if isinstance(n, ExitNode)), None)

    cfg = ControlFlowGraph(
        entry_node=entry_node,
        exit_node=exit_node,
    )
    cfg.nodes = nodes
    cfg.edges = edges

    return cfg


def test_dfg_from_json():
    """Test DFG building from JSON files."""
    print("=" * 80)
    print("DFG TEST FROM JSON FILES")
    print("=" * 80)
    print()

    # Load AST from JSON
    print("1. Loading AST from JSON...")
    with open("tests/cobol_samples/ast.json") as f:
        ast_data = json.load(f)

    ast = deserialize_program_node(ast_data["ast"])
    print(f"   ✓ AST loaded: {ast.program_name}")
    print(f"   ✓ Divisions: {len(ast.divisions)}")
    print()

    # Load CFG from JSON
    print("2. Loading CFG from JSON...")
    with open("tests/cobol_samples/cfg.json") as f:
        cfg_data = json.load(f)

    cfg = deserialize_control_flow_graph(cfg_data)
    print("   ✓ CFG loaded")
    print(f"   ✓ Nodes: {len(cfg.nodes)}")
    print(f"   ✓ Edges: {len(cfg.edges)}")
    print()

    # Build DFG
    print("3. Building DFG...")
    try:
        dfg = build_dfg(ast, cfg)
        print("   ✓ DFG built successfully")
        print(f"   ✓ DFG nodes: {len(dfg.nodes)}")
        print(f"   ✓ DFG edges: {len(dfg.edges)}")
        print()
    except Exception as e:
        print(f"   ✗ DFG build failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Analyze DFG
    print("4. Analyzing DFG...")

    # Count node types
    node_types = {}
    for node in dfg.nodes:
        node_type = type(node).__name__
        node_types[node_type] = node_types.get(node_type, 0) + 1

    print("   Node types:")
    for node_type, count in sorted(node_types.items()):
        print(f"   - {node_type}: {count}")
    print()

    # Extract unique variables
    variables = set()
    for node in dfg.nodes:
        if hasattr(node, "variable_name"):
            variables.add(node.variable_name)

    print(f"   Unique variables: {len(variables)}")
    for var in sorted(variables):
        print(f"   - {var}")
    print()

    # Show sample nodes
    print("   Sample DFG nodes (first 5):")
    for i, node in enumerate(dfg.nodes[:5], 1):
        node_type = type(node).__name__
        var_name = node.variable_name if hasattr(node, "variable_name") else "N/A"
        print(f"   [{i}] {node.node_id}: {node_type} ({var_name})")
    print()

    # Show sample edges
    if dfg.edges:
        print("   Sample DFG edges (first 5):")
        for i, edge in enumerate(dfg.edges[:5], 1):
            edge_type = edge.edge_type if hasattr(edge, "edge_type") else "unknown"
            source = edge.source.node_id if hasattr(edge, "source") and edge.source else "?"
            target = edge.target.node_id if hasattr(edge, "target") and edge.target else "?"
            print(f"   [{i}] {source} → {target} ({edge_type})")
        print()

    # Verification
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()

    success = True

    # Check 1: DFG has nodes
    if len(dfg.nodes) > 0:
        print(f"✓ DFG has nodes: {len(dfg.nodes)}")
    else:
        print("✗ DFG has no nodes")
        success = False

    # Check 2: DFG has edges
    if len(dfg.edges) > 0:
        print(f"✓ DFG has edges: {len(dfg.edges)}")
    else:
        print("⚠ DFG has no edges")

    # Check 3: Variables extracted
    expected_vars = [
        "WS-VALIDATION-RESULT",
        "WS-ERROR-MESSAGE",
        "WS-CHECK-COUNT",
        "LS-VALIDATION-CODE",
    ]
    found_vars = 0
    for var in expected_vars:
        if var in variables:
            print(f"✓ Variable found: {var}")
            found_vars += 1
        else:
            print(f"✗ Variable missing: {var}")
            success = False

    # Check 4: Expected node count
    if len(dfg.nodes) >= 20:
        print(f"✓ DFG has sufficient nodes: {len(dfg.nodes)} >= 20")
    else:
        print(f"⚠ DFG has fewer nodes than expected: {len(dfg.nodes)} < 20")

    print()

    if success:
        print("=" * 80)
        print("✅ SUCCESS: DFG test from JSON passed!")
        print("=" * 80)
        return 0
    else:
        print("=" * 80)
        print("❌ FAILURE: Some checks failed")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = test_dfg_from_json()
    sys.exit(exit_code)

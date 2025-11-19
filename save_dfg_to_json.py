"""Save DFG result to JSON file in tests/cobol_samples folder.

This script builds the DFG from the COBOL sample and serializes it to JSON
for future reference and testing.
"""

import json
import sys
from typing import Any


sys.path.insert(0, "src")

from src.core.models.cobol_analysis_model import (
    DFGEdge,
    VariableDefNode,
    VariableUseNode,
)
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.cobol_parser_antlr_service import parse_cobol
from src.core.services.dfg_builder_service import build_dfg


def serialize_variable_def_node(node: VariableDefNode) -> dict[str, Any]:
    """Serialize VariableDefNode to JSON."""
    result = {
        "node_type": "VariableDefNode",
        "node_id": node.node_id,
        "variable_name": node.variable_name,
        "location": node.location,
    }

    # Include basic statement info if available
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


def serialize_dfg(dfg) -> dict[str, Any]:
    """Serialize DataFlowGraph to JSON."""
    nodes = []
    for node in dfg.nodes:
        if isinstance(node, VariableDefNode):
            nodes.append(serialize_variable_def_node(node))
        elif isinstance(node, VariableUseNode):
            nodes.append(serialize_variable_use_node(node))
        else:
            # Generic fallback
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


def main():
    """Build DFG and save to JSON."""
    print("=" * 80)
    print("SAVING DFG TO JSON")
    print("=" * 80)
    print()

    # Read COBOL file
    print("1. Reading COBOL file...")
    cobol_file = "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"
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

    # Build CFG
    print("4. Building CFG...")
    cfg = build_cfg(ast)
    print(f"   ✓ CFG: {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")
    print()

    # Build DFG
    print("5. Building DFG...")
    dfg = build_dfg(ast, cfg)
    print(f"   ✓ DFG: {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")
    print()

    # Analyze DFG
    print("6. Analyzing DFG...")
    variables = set()
    for node in dfg.nodes:
        if hasattr(node, "variable_name"):
            variables.add(node.variable_name)

    print(f"   Variables: {len(variables)}")
    for var in sorted(variables):
        count = sum(1 for n in dfg.nodes if hasattr(n, "variable_name") and n.variable_name == var)
        print(f"   - {var}: {count} definitions")
    print()

    # Serialize to JSON
    print("7. Serializing to JSON...")
    dfg_data = serialize_dfg(dfg)
    print(f"   ✓ Serialized {len(dfg_data['nodes'])} nodes")
    print(f"   ✓ Serialized {len(dfg_data['edges'])} edges")
    print()

    # Save to file
    output_file = "tests/cobol_samples/dfg.json"
    print(f"8. Saving to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(dfg_data, f, indent=2)
    print(f"   ✓ Saved to {output_file}")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"DFG saved to: {output_file}")
    print(f"Nodes: {len(dfg_data['nodes'])}")
    print(f"Edges: {len(dfg_data['edges'])}")
    print(f"Variables: {len(variables)}")
    print()
    print("✅ DFG successfully saved to JSON!")
    print("=" * 80)


if __name__ == "__main__":
    main()

"""Debug control dependency detection in PDG."""

import sys


sys.path.insert(0, "src")

from src.core.models.cobol_analysis_model import CFGEdgeType, ControlFlowNode
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.cobol_parser_antlr_service import parse_cobol_file


def main():
    """Debug control dependency detection."""
    print("=" * 80)
    print("DEBUGGING CONTROL DEPENDENCY DETECTION")
    print("=" * 80)
    print()

    cobol_file = "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"

    # Build everything
    parsed = parse_cobol_file(cobol_file)
    ast = build_ast(parsed)
    cfg = build_cfg(ast)

    # Check CFG structure
    print("1. Checking CFG for branching nodes...")
    control_flow_nodes = [n for n in cfg.nodes if isinstance(n, ControlFlowNode)]
    print(f"   Found {len(control_flow_nodes)} ControlFlowNode instances")

    for node in control_flow_nodes:
        print(f"\n   Node: {node.node_id}")
        print(f"     Type: {node.control_type}")
        print(f"     Label: {node.label}")

        # Check edges from this node
        true_edges = [e for e in cfg.edges if e.source == node and e.edge_type == CFGEdgeType.TRUE]
        false_edges = [
            e for e in cfg.edges if e.source == node and e.edge_type == CFGEdgeType.FALSE
        ]

        print(f"     TRUE edges: {len(true_edges)}")
        for edge in true_edges:
            print(f"       -> {edge.target.node_id} ({edge.target.label})")

        print(f"     FALSE edges: {len(false_edges)}")
        for edge in false_edges:
            print(f"       -> {edge.target.node_id} ({edge.target.label})")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()

"""Debug PDG mapping issues."""

import sys


sys.path.insert(0, "src")

from src.core.models.cobol_analysis_model import BasicBlock, CFGEdgeType, ControlFlowNode
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.cobol_parser_antlr_service import parse_cobol_file


def main():
    """Debug PDG mapping."""
    print("=" * 80)
    print("DEBUGGING PDG MAPPING")
    print("=" * 80)
    print()

    cobol_file = "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"

    # Build everything
    parsed = parse_cobol_file(cobol_file)
    ast = build_ast(parsed)
    cfg = build_cfg(ast)

    # Check BasicBlock nodes to see which have statements
    print("1. Checking BasicBlock nodes with statements...")
    basic_blocks = [n for n in cfg.nodes if isinstance(n, BasicBlock)]
    print(f"   Found {len(basic_blocks)} BasicBlock instances")

    for node in basic_blocks:
        if node.statements:
            print(f"\n   Node: {node.node_id}")
            print(f"     Label: {node.label}")
            print(f"     Statements: {len(node.statements)}")
            for stmt in node.statements:
                print(f"       - {stmt.statement_type.name}")

    # Check control flow nodes and their targets
    print("\n\n2. Checking IF control flow and their target BasicBlocks...")
    control_flow_nodes = [
        n for n in cfg.nodes if isinstance(n, ControlFlowNode) and n.control_type == "IF"
    ]

    for cf_node in control_flow_nodes:
        print(f"\n   Control Flow Node: {cf_node.node_id}")
        print(f"     Label: {cf_node.label}")

        # Get TRUE and FALSE edges
        true_edges = [
            e for e in cfg.edges if e.source == cf_node and e.edge_type == CFGEdgeType.TRUE
        ]
        false_edges = [
            e for e in cfg.edges if e.source == cf_node and e.edge_type == CFGEdgeType.FALSE
        ]

        print("     TRUE targets:")
        for edge in true_edges:
            target = edge.target
            print(f"       -> {target.node_id} (type: {type(target).__name__})")
            if isinstance(target, BasicBlock) and target.statements:
                print(f"          Has {len(target.statements)} statements")
                for stmt in target.statements:
                    print(f"            - {stmt.statement_type.name}")

        print("     FALSE targets:")
        for edge in false_edges:
            target = edge.target
            print(f"       -> {target.node_id} (type: {type(target).__name__})")
            if isinstance(target, BasicBlock) and target.statements:
                print(f"          Has {len(target.statements)} statements")
                for stmt in target.statements:
                    print(f"            - {stmt.statement_type.name}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()

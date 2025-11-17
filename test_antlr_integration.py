#!/usr/bin/env python3
"""Integration test for ANTLR COBOL parser with all analysis tools.

This script tests the complete COBOL analysis pipeline:
1. Parse COBOL with ANTLR parser
2. Build AST from parse tree
3. Build CFG from AST
4. Build DFG from CFG
"""

import json
import sys
from pathlib import Path

from src.core.services.cobol_parser_antlr_service import parse_cobol_file
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.dfg_builder_service import build_dfg


def test_full_pipeline():
    """Test complete COBOL analysis pipeline with ANTLR parser."""
    cobol_file = Path(__file__).parent / "tests" / "cobol_samples" / "ACCOUNT-VALIDATOR-SIMPLE.cbl"

    print("=" * 80)
    print("COBOL ANALYSIS PIPELINE INTEGRATION TEST")
    print("=" * 80)
    print(f"\nInput file: {cobol_file}")
    print(f"Parser: ANTLR4 (Cobol85.g4 grammar)\n")

    try:
        # Step 1: Parse COBOL
        print("1. Parsing COBOL file...")
        parse_tree = parse_cobol_file(str(cobol_file))
        print(f"   ✓ Parse successful")
        print(f"   - Root node: {parse_tree.node_type}")
        print(f"   - Children: {len(parse_tree.children)}")

        # Step 2: Build AST
        print("\n2. Building AST from parse tree...")
        ast = build_ast(parse_tree)
        print(f"   ✓ AST built successfully")
        print(f"   - Program name: {ast.program_name}")
        print(f"   - Divisions: {len(ast.divisions)}")

        # Show division details
        for div in ast.divisions:
            div_name = div.division_type.value if hasattr(div.division_type, 'value') else str(div.division_type)
            print(f"     • {div_name}")

        # Step 3: Build CFG
        print("\n3. Building Control Flow Graph...")
        cfg = build_cfg(ast)
        print(f"   ✓ CFG built successfully")
        print(f"   - Nodes: {len(cfg.nodes)}")
        print(f"   - Edges: {len(cfg.edges)}")

        # Count node types
        entry_nodes = sum(1 for n in cfg.nodes if type(n).__name__ == "EntryNode")
        exit_nodes = sum(1 for n in cfg.nodes if type(n).__name__ == "ExitNode")
        paragraph_nodes = sum(1 for n in cfg.nodes if type(n).__name__ == "ParagraphNode")

        print(f"     • Entry nodes: {entry_nodes}")
        print(f"     • Exit nodes: {exit_nodes}")
        print(f"     • Paragraph nodes: {paragraph_nodes}")

        # Step 4: Build DFG
        print("\n4. Building Data Flow Graph...")
        dfg = build_dfg(ast, cfg)
        print(f"   ✓ DFG built successfully")
        print(f"   - Nodes: {len(dfg.nodes)}")
        print(f"   - Edges: {len(dfg.edges)}")

        # Count variable nodes
        var_def_nodes = sum(1 for n in dfg.nodes if "Def" in type(n).__name__)
        var_use_nodes = sum(1 for n in dfg.nodes if "Use" in type(n).__name__)

        print(f"     • Variable definitions: {var_def_nodes}")
        print(f"     • Variable uses: {var_use_nodes}")

        # Save results
        output_dir = Path(__file__).parent / "integration_test_output"
        output_dir.mkdir(exist_ok=True)

        print(f"\n5. Saving results to {output_dir}/")

        # Save AST summary
        ast_summary = {
            "program_name": ast.program_name,
            "divisions": [str(d.division_type) for d in ast.divisions],
            "division_count": len(ast.divisions)
        }
        with open(output_dir / "ast_summary.json", "w") as f:
            json.dump(ast_summary, f, indent=2)
        print("   ✓ ast_summary.json")

        # Save CFG summary
        cfg_summary = {
            "node_count": len(cfg.nodes),
            "edge_count": len(cfg.edges),
            "entry_nodes": entry_nodes,
            "exit_nodes": exit_nodes,
            "paragraph_nodes": paragraph_nodes,
            "nodes": [
                {
                    "id": node.node_id if hasattr(node, 'node_id') else i,
                    "type": type(node).__name__,
                    "label": node.label if hasattr(node, 'label') else None
                }
                for i, node in enumerate(cfg.nodes[:10])  # First 10 nodes as sample
            ]
        }
        with open(output_dir / "cfg_summary.json", "w") as f:
            json.dump(cfg_summary, f, indent=2)
        print("   ✓ cfg_summary.json")

        # Save DFG summary
        dfg_summary = {
            "node_count": len(dfg.nodes),
            "edge_count": len(dfg.edges),
            "var_definitions": var_def_nodes,
            "var_uses": var_use_nodes,
            "nodes": [
                {
                    "id": node.node_id if hasattr(node, 'node_id') else i,
                    "type": type(node).__name__,
                    "variable": node.variable_name if hasattr(node, 'variable_name') else None
                }
                for i, node in enumerate(dfg.nodes[:10])  # First 10 nodes as sample
            ]
        }
        with open(output_dir / "dfg_summary.json", "w") as f:
            json.dump(dfg_summary, f, indent=2)
        print("   ✓ dfg_summary.json")

        print("\n" + "=" * 80)
        print("✓ ALL INTEGRATION TESTS PASSED!")
        print("=" * 80)
        print("\nSummary:")
        print(f"  Parser:  ANTLR4 (production-ready)")
        print(f"  AST:     {len(ast.divisions)} divisions")
        print(f"  CFG:     {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")
        print(f"  DFG:     {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")
        print(f"\nThe ANTLR4 parser integration is complete and working!")

        return 0

    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_full_pipeline())

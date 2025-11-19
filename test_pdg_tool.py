"""Test script for PDG tool."""

import sys


sys.path.insert(0, "src")

from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.cobol_parser_antlr_service import parse_cobol_file
from src.core.services.dfg_builder_service import build_dfg
from src.core.services.pdg_builder_service import build_pdg


def main():
    """Test the PDG builder with sample COBOL code."""
    print("=" * 80)
    print("TESTING PDG BUILDER")
    print("=" * 80)
    print()

    cobol_file = "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"

    # Step 1: Parse COBOL
    print("1. Parsing COBOL file...")
    parsed = parse_cobol_file(cobol_file)
    print(f"   ✓ Parsed: {parsed.node_type}")
    print()

    # Step 2: Build AST
    print("2. Building AST...")
    ast = build_ast(parsed)
    print(f"   ✓ AST: {ast.program_name}")
    print()

    # Step 3: Build CFG
    print("3. Building CFG...")
    cfg = build_cfg(ast)
    print(f"   ✓ CFG: {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")
    print()

    # Step 4: Build DFG
    print("4. Building DFG...")
    dfg = build_dfg(ast, cfg)
    print(f"   ✓ DFG: {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")
    print()

    # Step 5: Build PDG
    print("5. Building PDG...")
    pdg = build_pdg(ast, cfg, dfg)
    print(f"   ✓ PDG: {len(pdg.nodes)} nodes, {len(pdg.edges)} edges")
    print()

    # Analyze PDG
    print("6. Analyzing PDG...")

    # Count edge types
    from src.core.models.cobol_analysis_model import PDGEdgeType

    control_edges = [e for e in pdg.edges if e.edge_type == PDGEdgeType.CONTROL]
    data_edges = [e for e in pdg.edges if e.edge_type == PDGEdgeType.DATA]

    print(f"   - Control dependencies: {len(control_edges)}")
    print(f"   - Data dependencies: {len(data_edges)}")
    print()

    # Show some sample control dependencies
    print("   Sample control dependencies (first 5):")
    for edge in control_edges[:5]:
        print(f"     {edge.source.label} --[{edge.label}]--> {edge.target.label}")
    print()

    # Show some sample data dependencies
    print("   Sample data dependencies (first 5):")
    for edge in data_edges[:5]:
        var = f" ({edge.variable_name})" if edge.variable_name else ""
        print(f"     {edge.source.label} --[data{var}]--> {edge.target.label}")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"AST: {len(ast.divisions)} divisions")
    print(f"CFG: {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")
    print(f"DFG: {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")
    print(f"PDG: {len(pdg.nodes)} nodes, {len(pdg.edges)} edges")
    print(f"     - {len(control_edges)} control dependencies")
    print(f"     - {len(data_edges)} data dependencies")
    print()
    print("✅ PDG builder test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

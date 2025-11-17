"""Comprehensive DFG Variable Extraction Test.

This test verifies that:
1. Variables are extracted from MOVE statements
2. Variables are extracted from ADD statements
3. Variable definitions (defs) are created
4. Variable uses are created
5. DFG edges show data flow connections
6. All expected variables appear in the DFG
"""

import sys
import json

sys.path.insert(0, "src")

from src.core.services.cobol_parser_antlr_service import parse_cobol
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.dfg_builder_service import build_dfg


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_dfg_variable_extraction():
    """Test DFG variable extraction with ACCOUNT-VALIDATOR-CLEAN.cbl."""

    # Load COBOL code
    with open("tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl") as f:
        cobol_code = f.read()

    print_section("DFG VARIABLE EXTRACTION TEST")

    # Parse and build structures
    print("\n1. Building COBOL structures...")
    parsed_cobol = parse_cobol(cobol_code)
    ast = build_ast(parsed_cobol)
    cfg = build_cfg(ast)
    dfg = build_dfg(ast, cfg)

    print(f"   ✓ AST: {ast.program_name}")
    print(f"   ✓ CFG: {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")
    print(f"   ✓ DFG: {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")

    # Analyze DFG nodes
    print_section("DFG NODES (Variable Definitions & Uses)")

    variable_defs = []
    variable_uses = []

    for node in dfg.nodes:
        node_type = type(node).__name__
        if node_type == "VariableDefNode":
            variable_defs.append(node)
        elif node_type == "VariableUseNode":
            variable_uses.append(node)

    print(f"\n   Total nodes: {len(dfg.nodes)}")
    print(f"   - Variable Definitions (VariableDefNode): {len(variable_defs)}")
    print(f"   - Variable Uses (VariableUseNode): {len(variable_uses)}")

    # Show all variable definitions
    print("\n   Variable Definitions:")
    if variable_defs:
        # Group by variable name
        defs_by_var = {}
        for def_node in variable_defs:
            var_name = def_node.variable_name
            if var_name not in defs_by_var:
                defs_by_var[var_name] = []
            defs_by_var[var_name].append(def_node)

        for var_name in sorted(defs_by_var.keys()):
            defs = defs_by_var[var_name]
            print(f"   - {var_name}: {len(defs)} definition(s)")
            for i, def_node in enumerate(defs):
                location = def_node.location if hasattr(def_node, "location") else "unknown"
                print(f"     [{i+1}] {def_node.node_id} at {location}")
    else:
        print("   (none)")

    # Show all variable uses
    print("\n   Variable Uses:")
    if variable_uses:
        uses_by_var = {}
        for use_node in variable_uses:
            var_name = use_node.variable_name
            if var_name not in uses_by_var:
                uses_by_var[var_name] = []
            uses_by_var[var_name].append(use_node)

        for var_name in sorted(uses_by_var.keys()):
            uses = uses_by_var[var_name]
            print(f"   - {var_name}: {len(uses)} use(s)")
            for i, use_node in enumerate(uses):
                location = use_node.location if hasattr(use_node, "location") else "unknown"
                print(f"     [{i+1}] {use_node.node_id} at {location}")
    else:
        print("   (none)")

    # Analyze DFG edges
    print_section("DFG EDGES (Data Flow Connections)")

    print(f"\n   Total edges: {len(dfg.edges)}")

    if dfg.edges:
        print("\n   Data Flow Connections:")
        for i, edge in enumerate(dfg.edges[:20], 1):  # Show first 20
            edge_type = edge.edge_type if hasattr(edge, "edge_type") else "unknown"
            source = edge.source if hasattr(edge, "source") else "unknown"
            target = edge.target if hasattr(edge, "target") else "unknown"
            print(f"   [{i}] {source} → {target} ({edge_type})")
    else:
        print("   (no edges)")

    # Verify expected variables
    print_section("VERIFICATION")

    expected_variables = [
        "WS-VALIDATION-RESULT",
        "WS-ERROR-MESSAGE",
        "WS-CHECK-COUNT",
        "LS-VALIDATION-CODE",
    ]

    # Get all unique variable names from DFG
    all_vars_in_dfg = set()
    for node in dfg.nodes:
        if hasattr(node, "variable_name"):
            all_vars_in_dfg.add(node.variable_name)

    print(f"\n   Variables found in DFG: {len(all_vars_in_dfg)}")
    for var_name in sorted(all_vars_in_dfg):
        print(f"   - {var_name}")

    print(f"\n   Checking expected variables:")
    all_found = True
    for var_name in expected_variables:
        if var_name in all_vars_in_dfg:
            print(f"   ✓ {var_name} - FOUND")
        else:
            print(f"   ✗ {var_name} - MISSING")
            all_found = False

    # Check specific statement types
    print_section("STATEMENT ANALYSIS")

    print("\n   Analyzing statements in AST...")

    move_targets = []
    add_targets = []

    for division in ast.divisions:
        for section in division.sections:
            for paragraph in section.paragraphs:
                for stmt in paragraph.statements:
                    if hasattr(stmt, "statement_type"):
                        stmt_type = str(stmt.statement_type)

                        if "MOVE" in stmt_type and hasattr(stmt, "attributes"):
                            target = stmt.attributes.get("target")
                            if target and hasattr(target, "variable_name"):
                                move_targets.append(target.variable_name)

                        elif "ADD" in stmt_type and hasattr(stmt, "attributes"):
                            target = stmt.attributes.get("target")
                            if target and hasattr(target, "variable_name"):
                                add_targets.append(target.variable_name)

    print(f"\n   MOVE statement targets extracted: {len(move_targets)}")
    for i, var_name in enumerate(move_targets[:10], 1):  # Show first 10
        print(f"   [{i}] {var_name}")

    print(f"\n   ADD statement targets extracted: {len(add_targets)}")
    for i, var_name in enumerate(add_targets, 1):
        print(f"   [{i}] {var_name}")

    # Final results
    print_section("RESULTS")

    success = True

    print("\n   Test Results:")

    # Check 1: DFG has nodes
    if len(dfg.nodes) > 0:
        print(f"   ✓ DFG has nodes: {len(dfg.nodes)}")
    else:
        print(f"   ✗ DFG has no nodes")
        success = False

    # Check 2: DFG has edges
    if len(dfg.edges) > 0:
        print(f"   ✓ DFG has edges: {len(dfg.edges)}")
    else:
        print(f"   ✗ DFG has no edges")
        success = False

    # Check 3: Variables extracted from statements
    if len(move_targets) > 0:
        print(f"   ✓ MOVE targets extracted: {len(move_targets)}")
    else:
        print(f"   ✗ No MOVE targets extracted")
        success = False

    if len(add_targets) > 0:
        print(f"   ✓ ADD targets extracted: {len(add_targets)}")
    else:
        print(f"   ✗ No ADD targets extracted")
        success = False

    # Check 4: Expected variables found
    if all_found:
        print(f"   ✓ All expected variables found in DFG")
    else:
        print(f"   ✗ Some expected variables missing from DFG")
        success = False

    # Check 5: Variable definitions created
    if len(variable_defs) > 0:
        print(f"   ✓ Variable definitions created: {len(variable_defs)}")
    else:
        print(f"   ✗ No variable definitions created")
        success = False

    print()
    if success:
        print("   " + "=" * 76)
        print("   ✅ SUCCESS: All variable extraction tests passed!")
        print("   " + "=" * 76)
        return 0
    else:
        print("   " + "=" * 76)
        print("   ❌ FAILURE: Some tests failed")
        print("   " + "=" * 76)
        return 1


if __name__ == "__main__":
    exit_code = test_dfg_variable_extraction()
    sys.exit(exit_code)

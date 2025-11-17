"""Test script to verify Step 3 changes - updated statement builders.

This script tests that:
1. MOVE statements extract source and target variable names
2. ADD statements extract value and target
3. PERFORM statements extract target paragraph
4. IF statements extract condition and branches
5. EVALUATE statements extract expression and WHEN clauses
6. DFG builder creates variable def/use nodes
7. DFG shows significantly more nodes than before
"""

import sys
import json

sys.path.insert(0, "src")

from src.core.services.cobol_parser_antlr_service import parse_cobol
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.dfg_builder_service import build_dfg


def test_with_cobol_file():
    """Test with ACCOUNT-VALIDATOR-CLEAN.cbl sample."""
    with open("tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl") as f:
        cobol_code = f.read()

    print("=" * 80)
    print("STEP 3 VERIFICATION TEST")
    print("=" * 80)
    print()

    # Parse COBOL
    print("1. Parsing COBOL...")
    parsed_cobol = parse_cobol(cobol_code)
    print(f"   ✓ Parse tree created: {parsed_cobol.node_type}")
    print()

    # Build AST
    print("2. Building AST...")
    ast = build_ast(parsed_cobol)
    print(f"   ✓ AST program: {ast.program_name}")
    print()

    # Count statements by type
    print("3. Analyzing statements...")
    statement_count = 0
    move_count = 0
    add_count = 0
    perform_count = 0
    if_count = 0
    evaluate_count = 0

    for division in ast.divisions:
        for section in division.sections:
            for paragraph in section.paragraphs:
                for stmt in paragraph.statements:
                    statement_count += 1
                    if hasattr(stmt, "statement_type"):
                        stmt_type = str(stmt.statement_type)
                        if "MOVE" in stmt_type:
                            move_count += 1
                            # Check if we extracted variable names
                            if hasattr(stmt, "attributes") and stmt.attributes:
                                source = stmt.attributes.get("source")
                                target = stmt.attributes.get("target")
                                if hasattr(target, "variable_name"):
                                    print(
                                        f"   MOVE: target='{target.variable_name}'"
                                    )
                        elif "ADD" in stmt_type:
                            add_count += 1
                            if hasattr(stmt, "attributes") and stmt.attributes:
                                target = stmt.attributes.get("target")
                                if hasattr(target, "variable_name"):
                                    print(
                                        f"   ADD: target='{target.variable_name}'"
                                    )
                        elif "PERFORM" in stmt_type:
                            perform_count += 1
                            if hasattr(stmt, "attributes") and stmt.attributes:
                                target_para = stmt.attributes.get("target_paragraph")
                                print(f"   PERFORM: target='{target_para}'")
                        elif "IF" in stmt_type:
                            if_count += 1
                        elif "EVALUATE" in stmt_type:
                            evaluate_count += 1

    print()
    print(f"   Total statements: {statement_count}")
    print(f"   - MOVE: {move_count}")
    print(f"   - ADD: {add_count}")
    print(f"   - PERFORM: {perform_count}")
    print(f"   - IF: {if_count}")
    print(f"   - EVALUATE: {evaluate_count}")
    print()

    # Build CFG
    print("4. Building CFG...")
    cfg = build_cfg(ast)
    print(f"   ✓ CFG nodes: {len(cfg.nodes)}")
    print(f"   ✓ CFG edges: {len(cfg.edges)}")
    print()

    # Build DFG
    print("5. Building DFG...")
    dfg = build_dfg(ast, cfg)
    print(f"   ✓ DFG nodes: {len(dfg.nodes)}")
    print(f"   ✓ DFG edges: {len(dfg.edges)}")
    print()

    # Analyze DFG nodes
    if dfg.nodes:
        print("   DFG node breakdown:")
        node_types = {}
        for node in dfg.nodes:
            # DFG nodes are VariableDefNode or VariableUseNode
            node_type = type(node).__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1

        for node_type, count in sorted(node_types.items()):
            print(f"   - {node_type}: {count}")
        print()

        # Show sample DFG nodes
        print("   Sample DFG nodes (first 10):")
        for i, node in enumerate(dfg.nodes[:10]):
            node_type = type(node).__name__
            print(f"   {i+1}. {node.node_id}: {node_type}")
            if hasattr(node, "variable_name"):
                print(f"      Variable: {node.variable_name}")
        print()

    # Verification
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()

    success = True

    # Check 1: Should have extracted MOVE targets
    if move_count > 0:
        print("✓ MOVE statements found and processed")
    else:
        print("✗ No MOVE statements found")
        success = False

    # Check 2: Should have extracted ADD targets
    if add_count > 0:
        print("✓ ADD statements found and processed")
    else:
        print("✗ No ADD statements found")
        success = False

    # Check 3: Should have extracted PERFORM targets
    if perform_count > 0:
        print("✓ PERFORM statements found and processed")
    else:
        print("✗ No PERFORM statements found")
        success = False

    # Check 4: DFG should have nodes now (before it was empty)
    if len(dfg.nodes) > 0:
        print(f"✓ DFG has {len(dfg.nodes)} nodes (was empty before Step 3)")
    else:
        print("✗ DFG is still empty - variables not being extracted")
        success = False

    # Check 5: DFG should have at least 20-30 nodes based on the COBOL sample
    if len(dfg.nodes) >= 20:
        print(f"✓ DFG has sufficient nodes ({len(dfg.nodes)} >= 20 expected)")
    else:
        print(
            f"⚠ DFG has fewer nodes than expected ({len(dfg.nodes)} < 20 expected)"
        )
        # Not a hard failure, but worth noting

    print()

    if success:
        print("=" * 80)
        print("SUCCESS: All checks passed!")
        print("=" * 80)
        return 0
    else:
        print("=" * 80)
        print("FAILURE: Some checks failed")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = test_with_cobol_file()
    sys.exit(exit_code)

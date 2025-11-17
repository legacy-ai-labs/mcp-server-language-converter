#!/usr/bin/env python3
"""Test the complete workflow: parse_cobol → build_cfg → build_dfg."""

import json

from src.core.services.tool_handlers_service import (
    build_cfg_handler,
    build_dfg_handler,
    parse_cobol_handler,
)


print("=" * 80)
print("COMPLETE WORKFLOW TEST: parse_cobol → build_cfg → build_dfg")
print("=" * 80)

# Step 1: Parse COBOL
print("\nSTEP 1: Parse COBOL")
print("-" * 80)
parse_result = parse_cobol_handler({"file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"})

if not parse_result.get("success"):
    print(f"❌ Parse failed: {parse_result.get('error')}")
    exit(1)

print("✅ Parse successful!")
print(f"   Program: {parse_result.get('program_name')}")

# Check statement counts in AST
ast = parse_result["ast"]
total_statements = 0
for division in ast.get("divisions", []):
    if division.get("division_type") == "PROCEDURE":
        for section in division.get("sections", []):
            for para in section.get("paragraphs", []):
                stmt_count = len(para.get("statements", []))
                total_statements += stmt_count
                print(f"   Paragraph '{para.get('paragraph_name')}': {stmt_count} statements")

print(f"   Total statements in AST: {total_statements}")

# Step 2: Build CFG
print("\nSTEP 2: Build CFG")
print("-" * 80)
cfg_result = build_cfg_handler({"ast": parse_result["ast"]})

if not cfg_result.get("success"):
    print(f"❌ CFG build failed: {cfg_result.get('error')}")
    exit(1)

print("✅ CFG build successful!")
print(f"   Nodes: {cfg_result.get('node_count')}")
print(f"   Edges: {cfg_result.get('edge_count')}")

# Step 3: Build DFG
print("\nSTEP 3: Build DFG")
print("-" * 80)
dfg_result = build_dfg_handler({"ast": parse_result["ast"], "cfg": cfg_result["cfg"]})

if not dfg_result.get("success"):
    print(f"❌ DFG build failed: {dfg_result.get('error')}")
    print(f"   Error details: {dfg_result}")
    exit(1)

print("✅ DFG build successful!")
print(f"   Nodes: {dfg_result.get('node_count')}")
print(f"   Edges: {dfg_result.get('edge_count')}")

if dfg_result.get("node_count") == 0:
    print("\n⚠️  WARNING: DFG is empty (no nodes)!")
    print("   This is expected because the AST has no statements.")
    print("   The parser is not yet extracting statement details from COBOL code.")
    print("\n   Current parser status:")
    print("   ✅ Program name extraction: Working")
    print("   ✅ Division identification: Working")
    print("   ✅ Paragraph name extraction: Working")
    print("   ❌ Statement parsing: Not yet implemented")
else:
    print("\nDFG Details:")
    dfg = dfg_result["dfg"]
    print(f"  Nodes: {len(dfg.get('nodes', []))}")
    for node in dfg.get("nodes", [])[:10]:  # Show first 10
        print(f"    - {node.get('node_id')}: {node.get('variable_name')}")
    print(f"  Edges: {len(dfg.get('edges', []))}")
    for edge in dfg.get("edges", [])[:10]:  # Show first 10
        print(f"    - {edge.get('source_id')} → {edge.get('target_id')} [{edge.get('edge_type')}]")

# Save results
print("\nSTEP 4: Save Results")
print("-" * 80)
with open("dfg_workflow_output.json", "w") as f:
    json.dump(
        {"parse_result": parse_result, "cfg_result": cfg_result, "dfg_result": dfg_result},
        f,
        indent=2,
    )
print("✅ Results saved to: dfg_workflow_output.json")

print("\n" + "=" * 80)
print("WORKFLOW COMPLETE")
print("=" * 80)

#!/usr/bin/env python3
"""Test script for COBOL parse → build_cfg workflow."""

import json
from src.core.services.tool_handlers_service import (
    parse_cobol_handler,
    build_cfg_handler,
)


def test_cfg_workflow():
    """Test the complete workflow: parse COBOL → build CFG."""

    # Step 1: Parse the COBOL file
    print("=" * 80)
    print("STEP 1: Parsing COBOL file")
    print("=" * 80)

    parse_result = parse_cobol_handler({
        "file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"
    })

    if not parse_result.get("success"):
        print(f"❌ Parse failed: {parse_result.get('error')}")
        return

    print(f"✅ Parse successful!")
    print(f"   Program name: {parse_result.get('program_name')}")
    print(f"   AST type: {parse_result['ast']['type']}")

    # Step 2: Build CFG from AST
    print("\n" + "=" * 80)
    print("STEP 2: Building Control Flow Graph")
    print("=" * 80)

    cfg_result = build_cfg_handler({
        "ast": parse_result["ast"]
    })

    if not cfg_result.get("success"):
        print(f"❌ CFG build failed: {cfg_result.get('error')}")
        return

    print(f"✅ CFG build successful!")
    print(f"   Node count: {cfg_result.get('node_count')}")
    print(f"   Edge count: {cfg_result.get('edge_count')}")

    # Step 3: Display CFG structure
    print("\n" + "=" * 80)
    print("STEP 3: CFG Structure Analysis")
    print("=" * 80)

    cfg = cfg_result["cfg"]

    print(f"\nEntry Node: {cfg['entry_node']['node_id']}")
    print(f"Exit Node: {cfg['exit_node']['node_id']}")

    print(f"\nNodes ({len(cfg['nodes'])}):")
    for node in cfg["nodes"]:
        node_type = node.get("node_type", "Unknown")
        node_id = node.get("node_id")
        label = node.get("label", "")
        print(f"  - {node_id:30} [{node_type:20}] {label}")

    print(f"\nEdges ({len(cfg['edges'])}):")
    for edge in cfg["edges"]:
        source = edge["source_id"]
        target = edge["target_id"]
        edge_type = edge["edge_type"]
        label = edge.get("label", "")
        print(f"  - {source:30} → {target:30} [{edge_type:15}] {label}")

    # Step 4: Save results to file
    print("\n" + "=" * 80)
    print("STEP 4: Saving Results")
    print("=" * 80)

    output_file = "cfg_test_output.json"
    with open(output_file, "w") as f:
        json.dump({
            "parse_result": parse_result,
            "cfg_result": cfg_result
        }, f, indent=2)

    print(f"✅ Results saved to: {output_file}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE - All steps successful! ✅")
    print("=" * 80)


if __name__ == "__main__":
    test_cfg_workflow()

#!/usr/bin/env python3
"""Check what's in a MOVE statement node."""

import json


# Load parse tree
with open("raw_parse_tree_output.json") as f:
    tree = json.load(f)


def find_first_move(node, depth=0):
    """Find first MOVE_STATEMENT node."""
    if isinstance(node, dict):
        if "MOVE" in node.get("node_type", ""):
            return node, depth

        for child in node.get("children", []):
            result, d = find_first_move(child, depth + 1)
            if result:
                return result, d

    return None, 0


move_node, depth = find_first_move(tree)

if move_node:
    print("Found MOVE statement node:")
    print(f"  Type: {move_node.get('node_type')}")
    print(f"  Depth: {depth}")
    print(f"  Children count: {len(move_node.get('children', []))}")
    print("\n  Children types:")
    for i, child in enumerate(move_node.get("children", [])[:10]):
        if isinstance(child, dict):
            print(f"    [{i}] {child.get('node_type')}: {child.get('value')}")
        else:
            print(f"    [{i}] {type(child).__name__}: {child}")

    # Show full structure
    print("\n  Full structure (first 500 chars):")
    print(json.dumps(move_node, indent=2)[:500])
else:
    print("No MOVE statement found")

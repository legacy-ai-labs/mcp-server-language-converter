#!/usr/bin/env python3
"""Investigate ANTLR parse tree structure for all statement types.

This script examines the parse tree to find the actual node names used
by the ANTLR grammar for each COBOL statement type.
"""

import json
from pathlib import Path


def find_nodes_by_type(node, target_type, max_results=5):
    """Find nodes matching a type pattern."""
    results = []

    def search(n, depth=0):
        if len(results) >= max_results:
            return

        if isinstance(n, dict):
            node_type = n.get("node_type", "")
            if target_type.upper() in node_type.upper():
                results.append({"node": n, "depth": depth})

            for child in n.get("children", []):
                search(child, depth + 1)

    search(node)
    return results


def show_node_structure(node, max_depth=3, current_depth=0, indent=""):
    """Recursively show node structure."""
    if not isinstance(node, dict) or current_depth >= max_depth:
        return []

    lines = []
    node_type = node.get("node_type", "UNKNOWN")
    value = node.get("value")

    # Format the node info
    if value and value != node_type:
        line = f"{indent}├─ {node_type}: '{value}'"
    else:
        line = f"{indent}├─ {node_type}"

    lines.append(line)

    # Show children
    children = node.get("children", [])
    for i, child in enumerate(children):
        if isinstance(child, dict):
            is_last = i == len(children) - 1
            child_indent = indent + ("   " if is_last else "│  ")
            lines.extend(show_node_structure(child, max_depth, current_depth + 1, child_indent))

    return lines


def investigate_statement_type(tree, statement_keyword, description):
    """Investigate a specific statement type."""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print("=" * 80)

    results = find_nodes_by_type(tree, statement_keyword, max_results=2)

    if not results:
        print(f"❌ No {statement_keyword} nodes found")
        return

    print(f"✅ Found {len(results)} example(s)\n")

    for idx, result in enumerate(results):
        node = result["node"]
        print(f"Example {idx + 1}:")
        print(f"  Node type: {node.get('node_type')}")
        print(f"  Line: {node.get('line_number')}")
        print("\n  Structure (3 levels deep):")

        structure_lines = show_node_structure(node, max_depth=3)
        for line in structure_lines:
            print(f"  {line}")

        # Extract key information
        print("\n  Key child node types:")
        for child in node.get("children", [])[:10]:
            if isinstance(child, dict):
                child_type = child.get("node_type")
                print(f"    - {child_type}")

        print()


def main():
    """Main investigation function."""
    print("=" * 80)
    print("COBOL Statement Structure Investigation")
    print("=" * 80)
    print("\nThis script investigates the ANTLR parse tree to find the actual")
    print("node names used for each COBOL statement type.\n")

    # Load the parse tree
    parse_tree_file = Path("raw_parse_tree_output.json")
    if not parse_tree_file.exists():
        print(f"❌ Error: {parse_tree_file} not found")
        print("   Run this first: uv run python test_raw_parse_tree.py")
        return

    with open(parse_tree_file) as f:
        tree = json.load(f)

    print(f"✅ Loaded parse tree from {parse_tree_file}\n")

    # Investigate each statement type
    statement_types = [
        ("MOVE", "1. MOVE Statement"),
        ("PERFORM", "2. PERFORM Statement"),
        ("IF", "3. IF Statement"),
        ("ADD", "4. ADD Statement"),
        ("EVALUATE", "5. EVALUATE Statement"),
        ("EXIT", "6. EXIT Statement"),
        ("COMPUTE", "7. COMPUTE Statement (if present)"),
        ("CALL", "8. CALL Statement (if present)"),
        ("READ", "9. READ Statement (if present)"),
        ("WRITE", "10. WRITE Statement (if present)"),
        ("DISPLAY", "11. DISPLAY Statement (if present)"),
    ]

    for keyword, description in statement_types:
        investigate_statement_type(tree, keyword, description)

    # Summary
    print("\n" + "=" * 80)
    print("INVESTIGATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review the structures above")
    print("2. Create a mapping document (ANTLR_NODE_MAPPING.md)")
    print("3. Update statement builders to use correct node names")
    print("4. Test variable extraction")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

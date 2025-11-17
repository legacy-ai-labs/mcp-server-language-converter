#!/usr/bin/env python3
"""Analyze parse tree structure to understand statement organization."""

import json

# Load the raw parse tree
with open("raw_parse_tree_output.json", "r") as f:
    parse_tree = json.load(f)

def find_path_to_node(node, target_type, current_path=""):
    """Find paths to nodes of a specific type."""
    if not isinstance(node, dict):
        return []

    paths = []
    node_type = node.get("node_type", "")
    new_path = f"{current_path}/{node_type}" if current_path else node_type

    if target_type.lower() in node_type.lower():
        paths.append(new_path)

    for child in node.get("children", []):
        paths.extend(find_path_to_node(child, target_type, new_path))

    return paths

def show_node_structure(node, target_type, max_depth=10):
    """Show the structure of nodes matching target type."""
    if not isinstance(node, dict):
        return []

    results = []
    node_type = node.get("node_type", "")

    if target_type.lower() in node_type.lower():
        # Found a match - show its structure
        children_types = [c.get("node_type") if isinstance(c, dict) else str(type(c).__name__)
                         for c in node.get("children", [])]
        results.append({
            "node_type": node_type,
            "children_count": len(node.get("children", [])),
            "children_types": children_types[:5]  # First 5 children
        })

    if max_depth > 0:
        for child in node.get("children", []):
            results.extend(show_node_structure(child, target_type, max_depth - 1))

    return results

print("=" * 80)
print("Parse Tree Structure Analysis")
print("=" * 80)

# Find all paragraph nodes
print("\n1. PARAGRAPH nodes and their children:")
print("-" * 80)
paragraphs = show_node_structure(parse_tree, "PARAGRAPH", max_depth=3)
for i, para in enumerate(paragraphs[:5]):
    print(f"\n[{i+1}] {para['node_type']} ({para['children_count']} children)")
    print(f"    Children types: {para['children_types']}")

# Find sentence nodes (which might contain statements)
print("\n\n2. SENTENCE nodes (might contain STATEMENT):")
print("-" * 80)
sentences = show_node_structure(parse_tree, "SENTENCE", max_depth=3)
for i, sent in enumerate(sentences[:5]):
    print(f"\n[{i+1}] {sent['node_type']} ({sent['children_count']} children)")
    print(f"    Children types: {sent['children_types']}")

# Find paths to STATEMENT nodes
print("\n\n3. Sample paths to STATEMENT nodes:")
print("-" * 80)
paths = find_path_to_node(parse_tree, "STATEMENT")
for i, path in enumerate(paths[:10]):
    # Show last few parts of path
    parts = path.split("/")[-6:]
    print(f"[{i+1}] .../{'/'.join(parts)}")

print("\n" + "=" * 80)

#!/usr/bin/env python3
"""Investigate the raw parse tree structure."""

import json
from src.core.services.tool_handlers_service import parse_cobol_raw_handler

print("Getting raw parse tree for ACCOUNT-VALIDATOR-CLEAN.cbl")
print("=" * 80)

result = parse_cobol_raw_handler({
    "file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"
})

if not result.get('success'):
    print(f"❌ Parse failed: {result.get('error')}")
    exit(1)

print(f"✅ Parse successful!")
print(f"Root node type: {result.get('node_type')}")

# Save the full parse tree
with open("raw_parse_tree_output.json", "w") as f:
    json.dump(result['parse_tree'], f, indent=2)

print("Raw parse tree saved to: raw_parse_tree_output.json")

# Look for paragraph nodes in the tree
def find_nodes_by_type(node, target_type, path=""):
    """Recursively find all nodes of a given type."""
    results = []

    if isinstance(node, dict):
        node_type = node.get('node_type', '')
        current_path = f"{path}/{node_type}"

        if target_type.lower() in node_type.lower():
            results.append({
                'path': current_path,
                'node_type': node_type,
                'value': node.get('value'),
                'children_count': len(node.get('children', []))
            })

        # Recurse into children
        for child in node.get('children', []):
            results.extend(find_nodes_by_type(child, target_type, current_path))

    return results

parse_tree = result['parse_tree']

print("\n" + "=" * 80)
print("Looking for PARAGRAPH nodes:")
print("=" * 80)
paragraph_nodes = find_nodes_by_type(parse_tree, 'paragraph')
for i, node in enumerate(paragraph_nodes[:10]):  # Show first 10
    print(f"\n[{i+1}] {node['node_type']}")
    print(f"    Path: {node['path']}")
    print(f"    Value: {node['value']}")
    print(f"    Children: {node['children_count']}")

print("\n" + "=" * 80)
print("Looking for NAME nodes:")
print("=" * 80)
name_nodes = find_nodes_by_type(parse_tree, 'name')
for i, node in enumerate(name_nodes[:20]):  # Show first 20
    print(f"[{i+1}] {node['node_type']:40} value='{node['value']}'")

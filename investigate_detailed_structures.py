#!/usr/bin/env python3
"""Deep investigation of statement structures to find variable/identifier nodes."""

import json
from pathlib import Path


def show_full_structure(node, max_depth=5, current_depth=0, indent="", show_values=True):
    """Show complete node structure with all details."""
    if not isinstance(node, dict) or current_depth >= max_depth:
        return []

    lines = []
    node_type = node.get("node_type", "UNKNOWN")
    value = node.get("value")

    # Format node
    if show_values and value and str(value).strip():
        line = f"{indent}├─ {node_type} = '{value}'"
    else:
        line = f"{indent}├─ {node_type}"

    lines.append(line)

    # Show children
    children = node.get("children", [])
    for i, child in enumerate(children):
        if isinstance(child, dict):
            is_last = (i == len(children) - 1)
            child_indent = indent + ("   " if is_last else "│  ")
            lines.extend(show_full_structure(child, max_depth, current_depth + 1, child_indent, show_values))

    return lines


def find_first_node(tree, node_type_pattern):
    """Find first node matching a pattern."""
    def search(node):
        if isinstance(node, dict):
            nt = node.get("node_type", "")
            if node_type_pattern.upper() in nt.upper() and node_type_pattern.upper() + "STATEMENT" == nt.upper():
                return node

            for child in node.get("children", []):
                result = search(child)
                if result:
                    return result
        return None

    return search(tree)


def investigate_detailed(tree, statement_type, description):
    """Show detailed structure for a statement type."""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print('=' * 80)

    node = find_first_node(tree, statement_type)

    if not node:
        print(f"❌ No {statement_type}STATEMENT nodes found\n")
        return

    print(f"Full structure (5 levels deep):\n")
    lines = show_full_structure(node, max_depth=5)
    for line in lines:
        print(line)


def extract_identifiers(node, path="", identifiers=None):
    """Recursively extract all IDENTIFIER nodes with their paths."""
    if identifiers is None:
        identifiers = []

    if isinstance(node, dict):
        node_type = node.get("node_type", "")
        new_path = f"{path}/{node_type}" if path else node_type

        if "IDENTIFIER" in node_type or "DATANAME" in node_type or "QUALIFIEDDATANAME" in node_type:
            value = node.get("value")
            identifiers.append({
                "path": new_path,
                "node_type": node_type,
                "value": value,
                "node": node
            })

        for child in node.get("children", []):
            extract_identifiers(child, new_path, identifiers)

    return identifiers


def show_identifier_locations(tree, statement_type):
    """Show where identifiers appear in a statement."""
    node = find_first_node(tree, statement_type)

    if not node:
        return

    identifiers = extract_identifiers(node)

    if identifiers:
        print(f"\n  Identifiers found in {statement_type}:")
        for ident in identifiers:
            # Show path from statement root
            parts = ident['path'].split('/')
            short_path = ' → '.join(parts[-4:])  # Last 4 parts
            print(f"    {short_path}")
            if ident['value']:
                # Try to get actual identifier value
                if ident['node'].get('children'):
                    for child in ident['node'].get('children', []):
                        if isinstance(child, dict) and child.get('value'):
                            print(f"      Value: '{child.get('value')}'")
                            break
                else:
                    print(f"      Value: '{ident['value']}'")


def main():
    """Main investigation."""
    print("=" * 80)
    print("DETAILED COBOL Statement Structure Investigation")
    print("=" * 80)
    print("\nShowing 5 levels deep to find where variable names are located\n")

    # Load parse tree
    parse_tree_file = Path("raw_parse_tree_output.json")
    if not parse_tree_file.exists():
        print(f"❌ Error: {parse_tree_file} not found")
        return

    with open(parse_tree_file) as f:
        tree = json.load(f)

    # Investigate key statement types in detail
    statements = [
        ("MOVE", "MOVE Statement - Full Structure"),
        ("ADD", "ADD Statement - Full Structure"),
        ("PERFORM", "PERFORM Statement - Full Structure"),
        ("IF", "IF Statement - Full Structure"),
        ("EVALUATE", "EVALUATE Statement - Full Structure"),
    ]

    for stmt_type, description in statements:
        investigate_detailed(tree, stmt_type, description)
        show_identifier_locations(tree, stmt_type)

    print("\n" + "=" * 80)
    print("DETAILED INVESTIGATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Test ANTLR-based COBOL parser with ACCOUNT-VALIDATOR.cbl"""

import json
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.services.cobol_parser_antlr_service import ParseNode, parse_cobol_file


def print_parse_tree(node: ParseNode, indent: int = 0) -> None:
    """Pretty-print the parse tree structure."""
    prefix = "  " * indent

    if node.value is not None:
        print(f"{prefix}{node.node_type}: {node.value}")
    else:
        print(f"{prefix}{node.node_type}")

    for child in node.children:
        print_parse_tree(child, indent + 1)


def node_to_dict(node: ParseNode) -> dict:
    """Convert ParseNode to dictionary for JSON serialization."""
    result = {
        "node_type": node.node_type,
    }

    if node.value is not None:
        result["value"] = node.value

    if node.line_number is not None:
        result["line_number"] = node.line_number

    if node.children:
        result["children"] = [node_to_dict(child) for child in node.children]

    return result


def main():
    """Main test function."""
    # Use simplified version without AUTHOR/DATE-WRITTEN paragraphs
    # (ANTLR grammar expects special comment format for those)
    cobol_file = Path(__file__).parent / "tests" / "cobol_samples" / "ACCOUNT-VALIDATOR-SIMPLE.cbl"

    print(f"Testing ANTLR COBOL parser with: {cobol_file}")
    print("=" * 80)

    try:
        # Parse the COBOL file
        print("\n1. Parsing COBOL file with ANTLR...")
        parse_tree = parse_cobol_file(str(cobol_file))
        print("✓ Parsing successful!")

        # Print parse tree structure (limited depth to avoid overwhelming output)
        print("\n2. Parse tree structure (limited to 3 levels):")
        print("-" * 80)

        def print_limited_depth(node: ParseNode, depth: int = 0, max_depth: int = 3) -> None:
            prefix = "  " * depth
            if node.value is not None:
                print(f"{prefix}{node.node_type}: {node.value}")
            else:
                print(f"{prefix}{node.node_type} ({len(node.children)} children)")

            if depth < max_depth:
                for child in node.children:
                    print_limited_depth(child, depth + 1, max_depth)

        print_limited_depth(parse_tree)

        # Save full tree to JSON for detailed inspection
        output_file = Path(__file__).parent / "parse_tree_antlr_output.json"
        print(f"\n3. Saving full parse tree to: {output_file}")
        with open(output_file, "w") as f:
            json.dump(node_to_dict(parse_tree), f, indent=2)
        print("✓ Parse tree saved!")

        # Extract key information
        print("\n4. Summary:")
        print("-" * 80)
        print("Parser: ANTLR4 (Cobol85.g4 grammar)")
        print(f"Input file: {cobol_file}")
        print(f"Parse tree root: {parse_tree.node_type}")
        print(f"Number of top-level children: {len(parse_tree.children)}")

        # Count nodes recursively
        def count_nodes(node: ParseNode) -> int:
            return 1 + sum(count_nodes(child) for child in node.children)

        total_nodes = count_nodes(parse_tree)
        print(f"Total nodes in tree: {total_nodes}")

        print("\n" + "=" * 80)
        print("✓ All tests completed successfully!")
        print("\nNext step: Compare with PLY parser output")

        return 0

    except SyntaxError as e:
        print(f"\n✗ Syntax Error: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"\n✗ File Not Found: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

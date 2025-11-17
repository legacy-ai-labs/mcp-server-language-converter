#!/usr/bin/env python3
"""Test script for COBOL parser service using ACCOUNT-VALIDATOR.cbl"""

import json
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.services.cobol_parser_service import ParseNode, _reset_parser, parse_cobol_file


# Force parser rebuild to pick up grammar changes
_reset_parser()


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

    if node.children:
        result["children"] = [node_to_dict(child) for child in node.children]

    return result


def main():
    """Main test function."""
    cobol_file = Path(__file__).parent / "tests" / "cobol_samples" / "ACCOUNT-VALIDATOR.cbl"

    print(f"Testing COBOL parser with: {cobol_file}")
    print("=" * 80)

    try:
        # Parse the COBOL file
        print("\n1. Parsing COBOL file...")
        parse_tree = parse_cobol_file(str(cobol_file))
        print("✓ Parsing successful!")

        # Print parse tree structure
        print("\n2. Parse tree structure:")
        print("-" * 80)
        print_parse_tree(parse_tree)

        # Save to JSON for detailed inspection
        output_file = Path(__file__).parent / "parse_tree_output.json"
        print(f"\n3. Saving parse tree to: {output_file}")
        with open(output_file, "w") as f:
            json.dump(node_to_dict(parse_tree), f, indent=2)
        print("✓ Parse tree saved!")

        # Extract key information
        print("\n4. Extracted Information:")
        print("-" * 80)

        # Find PROGRAM-ID
        for child in parse_tree.children:
            if child.node_type == "IDENTIFICATION_DIVISION":
                for id_child in child.children:
                    if id_child.node_type == "PROGRAM_ID":
                        print(f"Program ID: {id_child.value}")

        # Count sections
        for child in parse_tree.children:
            if child.node_type == "DATA_DIVISION":
                print("\nData Division sections:")
                for data_child in child.children:
                    if hasattr(data_child, "children"):
                        for section in data_child.children:
                            print(f"  - {section.node_type}")

        # Count paragraphs in PROCEDURE DIVISION
        paragraph_count = 0
        for child in parse_tree.children:
            if child.node_type == "PROCEDURE_DIVISION":
                for proc_child in child.children:
                    if proc_child.node_type == "PROCEDURE_BODY":
                        for body_child in proc_child.children:
                            if body_child.node_type == "PARAGRAPH":
                                paragraph_count += 1
                                # Get paragraph name
                                for para_child in body_child.children:
                                    if para_child.node_type == "PARAGRAPH_NAME":
                                        print(f"\nParagraph: {para_child.value}")

        print(f"\nTotal paragraphs: {paragraph_count}")

        print("\n" + "=" * 80)
        print("✓ All tests completed successfully!")

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

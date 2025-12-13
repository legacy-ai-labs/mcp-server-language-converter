"""Test script for COBOL parser."""

import sys
import traceback
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.services.cobol_analysis.cobol_parser_antlr_service import parse_cobol_file


def test_parser() -> None:
    """Test parser with sample COBOL files."""
    test_files = [
        "tests/cobol_samples/CUSTOMER-ACCOUNT-MAIN.cbl",
        "tests/cobol_samples/CALCULATE-PENALTY.cbl",
        "tests/cobol_samples/ACCOUNT-VALIDATOR.cbl",
    ]

    for file_path in test_files:
        print(f"\n{'='*60}")
        print(f"Testing: {file_path}")
        print("=" * 60)
        try:
            parse_node, comments, id_metadata = parse_cobol_file(file_path)
            print("✓ Parsed successfully!")
            print(f"  Root node type: {parse_node.node_type}")
            print(f"  Number of children: {len(parse_node.children)}")
            print(f"  Comments extracted: {len(comments)}")
            print(f"  Program AUTHOR: {id_metadata.author}")
            if parse_node.children:
                print(f"  Children types: {[c.node_type for c in parse_node.children]}")
        except Exception as e:
            print(f"✗ Parsing failed: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    test_parser()

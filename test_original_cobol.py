#!/usr/bin/env python3
"""Test parse_cobol tool with original ACCOUNT-VALIDATOR.cbl file."""

import sys

from src.core.services.tool_handlers_service import parse_cobol_handler


def test_original_file():
    """Test parsing original ACCOUNT-VALIDATOR.cbl."""
    print("=" * 80)
    print("Testing parse_cobol with ACCOUNT-VALIDATOR.cbl")
    print("=" * 80)

    result = parse_cobol_handler({"file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR.cbl"})

    if result["success"]:
        print("\n✅ SUCCESS!")
        print(f"Program name: {result['program_name']}")
        print(f"AST structure: {list(result['ast'].keys())}")

        # Show divisions
        if "divisions" in result["ast"]:
            print(f"\nDivisions found: {len(result['ast']['divisions'])}")
            for div in result["ast"]["divisions"]:
                print(f"  - {div.get('type', 'UNKNOWN')}")

        return True
    else:
        print("\n❌ FAILED")
        print(f"Error: {result['error']}")

        # Provide helpful guidance
        print("\n" + "=" * 80)
        print("TROUBLESHOOTING:")
        print("=" * 80)
        print("The ANTLR parser requires preprocessing for some COBOL constructs.")
        print("\nThe original file contains:")
        print("  • AUTHOR paragraph")
        print("  • DATE-WRITTEN paragraph")
        print("\nThese require special comment format (*>CE) in ANTLR grammar.")
        print("\nOptions:")
        print("  1. Use ACCOUNT-VALIDATOR-SIMPLE.cbl (already tested ✓)")
        print("  2. Remove AUTHOR/DATE-WRITTEN from the file")
        print("  3. Add preprocessor support (future enhancement)")

        return False


if __name__ == "__main__":
    success = test_original_file()
    sys.exit(0 if success else 1)

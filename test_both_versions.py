#!/usr/bin/env python3
"""Compare parsing results between original and cleaned COBOL files."""

import sys

from src.core.services.tool_handlers_service import parse_cobol_handler


def test_file(file_path: str, description: str) -> dict:
    """Test parsing a COBOL file."""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print(f"File: {file_path}")
    print("=" * 80)

    result = parse_cobol_handler({"file_path": file_path})

    if result["success"]:
        print("\n✅ SUCCESS!")
        print(f"  Program name: {result['program_name']}")
        print(f"  Divisions: {len(result['ast']['divisions'])}")

        # Show division types
        for i, div in enumerate(result["ast"]["divisions"], 1):
            div_type = div.get("division_type", "UNKNOWN")
            print(f"    {i}. {div_type}")
    else:
        print("\n❌ FAILED")
        print(f"  Error: {result['error']}")

        # Extract just the key error message
        if "line 3" in result["error"]:
            print("  Issue: AUTHOR/DATE-WRITTEN paragraphs not supported")

    return result


def main():
    """Compare original vs cleaned versions."""
    print("=" * 80)
    print("COBOL FILE PARSING COMPARISON")
    print("=" * 80)

    # Test original file
    original_result = test_file(
        "tests/cobol_samples/ACCOUNT-VALIDATOR.cbl", "TEST 1: Original ACCOUNT-VALIDATOR.cbl"
    )

    # Test cleaned file
    cleaned_result = test_file(
        "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl",
        "TEST 2: Cleaned ACCOUNT-VALIDATOR-CLEAN.cbl",
    )

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"Original file: {'✅ PASS' if original_result['success'] else '❌ FAIL'}")
    print(f"Cleaned file:  {'✅ PASS' if cleaned_result['success'] else '❌ FAIL'}")

    print("\nRECOMMENDATION:")
    if not original_result["success"] and cleaned_result["success"]:
        print("  Use the cleaned version or remove AUTHOR/DATE-WRITTEN paragraphs")
        print("  from your COBOL files before parsing.")
        print("\n  Automatic cleaning script:")
        print("    uv run python scripts/prepare_cobol_for_antlr.py <your_file.cbl>")

    return 0


if __name__ == "__main__":
    sys.exit(main())

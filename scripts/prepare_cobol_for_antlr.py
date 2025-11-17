#!/usr/bin/env python3
"""Prepare COBOL files for ANTLR parser by removing unsupported optional paragraphs.

The ANTLR Cobol85.g4 grammar expects AUTHOR, DATE-WRITTEN, etc. to use
special comment format (*>CE). This script removes these optional paragraphs
to make files compatible with the parser.
"""

import sys
from pathlib import Path


def remove_optional_paragraphs(cobol_source: str) -> str:
    """Remove optional identification division paragraphs.

    Removes:
    - AUTHOR paragraph
    - DATE-WRITTEN paragraph
    - DATE-COMPILED paragraph
    - INSTALLATION paragraph
    - SECURITY paragraph
    - REMARKS paragraph

    Args:
        cobol_source: Original COBOL source code

    Returns:
        Cleaned COBOL source code
    """
    lines = cobol_source.split("\n")
    cleaned_lines = []
    skip_line = False

    for line in lines:
        # Check if this is an optional paragraph header
        upper_line = line.upper().strip()

        if any(
            keyword in upper_line
            for keyword in [
                "AUTHOR.",
                "DATE-WRITTEN.",
                "DATE-COMPILED.",
                "INSTALLATION.",
                "SECURITY.",
                "REMARKS.",
            ]
        ):
            skip_line = True
            continue

        # Check if we've reached the next division or another paragraph
        if any(
            keyword in upper_line
            for keyword in [
                "DATA DIVISION",
                "ENVIRONMENT DIVISION",
                "PROCEDURE DIVISION",
                "PROGRAM-ID.",
            ]
        ):
            skip_line = False

        if not skip_line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def prepare_file(input_path: Path, output_path: Path | None = None) -> bool:
    """Prepare a COBOL file for ANTLR parser.

    Args:
        input_path: Path to original COBOL file
        output_path: Path for cleaned file (defaults to input_path with -CLEAN suffix)

    Returns:
        True if successful, False otherwise
    """
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        return False

    # Default output path
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}-CLEAN{input_path.suffix}"

    try:
        # Read original file
        print(f"Reading: {input_path}")
        original_content = input_path.read_text(encoding="utf-8")

        # Clean it
        print("Removing optional paragraphs...")
        cleaned_content = remove_optional_paragraphs(original_content)

        # Write cleaned version
        print(f"Writing: {output_path}")
        output_path.write_text(cleaned_content, encoding="utf-8")

        print("✅ Successfully prepared COBOL file!")
        print(f"   Original: {input_path}")
        print(f"   Cleaned:  {output_path}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Command-line interface."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/prepare_cobol_for_antlr.py <input_file> [output_file]")
        print("\nExample:")
        print(
            "  python scripts/prepare_cobol_for_antlr.py tests/cobol_samples/ACCOUNT-VALIDATOR.cbl"
        )
        print("  # Creates: tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    success = prepare_file(input_path, output_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

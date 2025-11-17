#!/usr/bin/env python3
"""Debug test for COBOL parser - check tokenization and parsing steps"""

import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.services.cobol_parser_service import get_lexer


def test_lexer(source_code: str):
    """Test just the lexer to see if tokenization works."""
    print("Testing Lexer:")
    print("=" * 80)

    lexer = get_lexer()
    lexer.input(source_code)

    tokens = []
    for tok in lexer:
        tokens.append(tok)
        print(f"Line {tok.lineno:3d}: {tok.type:20s} = {tok.value!r}")

    print(f"\nTotal tokens: {len(tokens)}")
    return tokens


def test_simple_cobol():
    """Test with a minimal COBOL program first."""
    simple_program = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SIMPLE.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-VAR PIC X(10).

       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY 'Hello'.
           EXIT PROGRAM.
    """

    # Normalize like the parser does
    simple_program = simple_program.upper().strip()

    print("Testing with simple COBOL program:")
    print("=" * 80)
    print(simple_program)
    print("=" * 80)

    try:
        from core.services.cobol_parser_service import parse_cobol

        result = parse_cobol(simple_program)
        print("\n✓ Simple program parsed successfully!")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"\n✗ Simple program failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_account_validator_tokens():
    """Test tokenization of ACCOUNT-VALIDATOR.cbl"""
    cobol_file = Path(__file__).parent / "tests" / "cobol_samples" / "ACCOUNT-VALIDATOR.cbl"

    print(f"\nTesting tokenization of: {cobol_file}")
    print("=" * 80)

    source_code = cobol_file.read_text()

    # Normalize like the parser does
    import re

    normalized_source = source_code.replace("\r\n", "\n").replace("\r", "\n")

    # Preserve string literals
    string_literals = []
    placeholder_pattern = r"'[^']*'"

    def replace_literal(match):
        literal = match.group(0)
        string_literals.append(literal)
        return f"__STRING_LITERAL_{len(string_literals)-1}__"

    source_with_placeholders = re.sub(placeholder_pattern, replace_literal, normalized_source)
    source_uppercased = source_with_placeholders.upper()

    for idx, literal in enumerate(string_literals):
        source_uppercased = source_uppercased.replace(f"__STRING_LITERAL_{idx}__", literal)

    normalized_source = source_uppercased

    # Just show first 20 lines of tokens
    print("\nFirst part of file (normalized):")
    print("-" * 80)
    lines = normalized_source.split("\n")[:15]
    for i, line in enumerate(lines, 1):
        print(f"{i:3d}: {line}")

    print("\n\nTokens around line 8 (WS-VALIDATION-RESULT):")
    print("-" * 80)

    test_lexer(normalized_source)


def main():
    """Main test function."""
    # First test with simple program
    print("STEP 1: Testing with minimal COBOL program")
    print("=" * 80)
    simple_ok = test_simple_cobol()

    print("\n\n")

    # Then test tokenization of actual file
    print("STEP 2: Testing tokenization of ACCOUNT-VALIDATOR.cbl")
    print("=" * 80)
    test_account_validator_tokens()

    return 0 if simple_ok else 1


if __name__ == "__main__":
    sys.exit(main())

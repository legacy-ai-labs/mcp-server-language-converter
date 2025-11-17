#!/usr/bin/env python3
"""Debug COBOL parsing with full output"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "src"))

# Reset parser
from core.services import cobol_parser_service


cobol_parser_service._parser = None
cobol_parser_service._lexer = None

import logging

from ply import yacc


# Enable full debug logging
logging.basicConfig(level=logging.DEBUG)


def test_with_debug():
    """Test with parser debugging enabled."""
    minimal = """
IDENTIFICATION DIVISION.
PROGRAM-ID. TEST.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 X PIC 9.
PROCEDURE DIVISION.
P1.
    EXIT PROGRAM.
""".strip().upper()

    print("Input:")
    print(minimal)
    print("\n" + "=" * 80)
    print("Parsing with debug...\n")

    lexer = cobol_parser_service.get_lexer()

    # Create parser with debug enabled
    parser = yacc.yacc(
        module=cobol_parser_service, debug=True, debuglog=logging.getLogger(), write_tables=False
    )

    result = parser.parse(minimal, lexer=lexer, debug=logging.getLogger())

    if result:
        print(f"\n✓ Success: {result}")
    else:
        print("\n✗ Failed: parser returned None")


if __name__ == "__main__":
    test_with_debug()

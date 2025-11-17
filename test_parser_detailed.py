#!/usr/bin/env python3
"""Detailed parser debugging to understand the issue"""

import sys
import logging
from pathlib import Path

# Setup logging to see parser debug output
logging.basicConfig(level=logging.DEBUG)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and force parser rebuild
from core.services import cobol_parser_service
cobol_parser_service._parser = None
cobol_parser_service._lexer = None

from ply import yacc

# Rebuild parser with debug output
from core.services.cobol_parser_service import get_lexer, get_parser


def test_minimal():
    """Test with absolute minimal COBOL."""
    minimal = """
IDENTIFICATION DIVISION.
PROGRAM-ID. TEST.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 X PIC 9.
PROCEDURE DIVISION.
P1.
    EXIT PROGRAM.
"""

    print("Testing minimal COBOL:")
    print("=" * 80)
    print(minimal)
    print("=" * 80)

    from core.services.cobol_parser_service import parse_cobol

    try:
        result = parse_cobol(minimal)
        print(f"\n✓ Success! Result: {result}")
        return True
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_parser_conflicts():
    """Check if parser has any conflicts."""
    print("\nChecking parser for conflicts...")
    print("=" * 80)

    # Force parser rebuild with debugging
    parser = yacc.yacc(
        module=cobol_parser_service,
        debug=True,
        debugfile='parser.out',
        write_tables=False
    )

    print("\n✓ Parser created. Check 'parser.out' for conflicts.")


if __name__ == "__main__":
    check_parser_conflicts()
    print("\n\n")
    test_minimal()

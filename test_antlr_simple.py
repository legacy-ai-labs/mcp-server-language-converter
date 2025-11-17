#!/usr/bin/env python3
"""Test ANTLR parser with minimal COBOL"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.services.cobol_parser_antlr_service import parse_cobol


# Minimal COBOL program (use TESTPROG, not TEST which is reserved)
minimal_cobol = """
IDENTIFICATION DIVISION.
PROGRAM-ID. TESTPROG.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 X PIC 9.
PROCEDURE DIVISION.
P1.
    EXIT PROGRAM.
"""

print("Testing ANTLR parser with minimal COBOL:")
print("=" * 80)
print(minimal_cobol)
print("=" * 80)

try:
    result = parse_cobol(minimal_cobol)
    print(f"\n✓ Success! Root node: {result.node_type}")
    print(f"Children: {len(result.children)}")
except Exception as e:
    print(f"\n✗ Failed: {e}")
    import traceback

    traceback.print_exc()

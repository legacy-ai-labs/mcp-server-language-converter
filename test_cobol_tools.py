#!/usr/bin/env python3
"""Test COBOL tools to verify ANTLR integration."""

import sys
from pathlib import Path

from src.core.services.tool_handlers_service import (
    parse_cobol_handler,
    parse_cobol_raw_handler,
    build_ast_handler,
    build_cfg_handler,
    build_dfg_handler,
)

def test_parse_cobol_tool():
    """Test parse_cobol tool handler."""
    print("Testing parse_cobol tool handler...")

    result = parse_cobol_handler({
        "file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-SIMPLE.cbl"
    })

    if result["success"]:
        print(f"  ✓ Success!")
        print(f"  Program: {result['program_name']}")
        print(f"  AST keys: {list(result['ast'].keys())}")
    else:
        print(f"  ✗ Failed: {result['error']}")

    return result["success"]


def test_parse_cobol_raw_tool():
    """Test parse_cobol_raw tool handler."""
    print("\nTesting parse_cobol_raw tool handler...")

    result = parse_cobol_raw_handler({
        "file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-SIMPLE.cbl"
    })

    if result["success"]:
        print(f"  ✓ Success!")
        print(f"  Root node: {result['node_type']}")
        print(f"  Parse tree keys: {list(result['parse_tree'].keys())}")
    else:
        print(f"  ✗ Failed: {result['error']}")

    return result["success"]


def test_full_pipeline():
    """Test full pipeline: parse → AST → CFG → DFG."""
    print("\nTesting full pipeline...")

    # Step 1: Parse COBOL
    parse_result = parse_cobol_handler({
        "file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-SIMPLE.cbl"
    })
    if not parse_result["success"]:
        print(f"  ✗ Parse failed: {parse_result['error']}")
        return False
    print(f"  ✓ Parse successful")

    # Step 2: Build CFG (parse_cobol_handler already builds AST)
    cfg_result = build_cfg_handler({
        "ast": parse_result["ast"]
    })
    if not cfg_result["success"]:
        print(f"  ✗ CFG failed: {cfg_result['error']}")
        return False
    print(f"  ✓ CFG successful: {cfg_result['node_count']} nodes")

    # Step 3: Build DFG
    dfg_result = build_dfg_handler({
        "ast": parse_result["ast"],
        "cfg": cfg_result["cfg"]
    })
    if not dfg_result["success"]:
        print(f"  ✗ DFG failed: {dfg_result['error']}")
        return False
    print(f"  ✓ DFG successful: {dfg_result['node_count']} nodes")

    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("COBOL TOOL HANDLERS TEST - VERIFYING ANTLR INTEGRATION")
    print("=" * 70)

    all_passed = True

    all_passed &= test_parse_cobol_tool()
    all_passed &= test_parse_cobol_raw_tool()
    all_passed &= test_full_pipeline()

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TOOL HANDLERS WORKING WITH ANTLR PARSER!")
    else:
        print("❌ Some tests failed")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

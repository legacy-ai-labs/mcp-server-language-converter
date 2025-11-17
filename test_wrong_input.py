#!/usr/bin/env python3
"""Test what happens if user passes wrong data to build_cfg."""

from src.core.services.tool_handlers_service import (
    build_cfg_handler,
    parse_cobol_handler,
)


print("=" * 80)
print("Testing various incorrect inputs to build_cfg")
print("=" * 80)

# Get a parse result
parse_result = parse_cobol_handler({"file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"})

# Test 1: Passing the whole parse_result instead of just the ast
print("\n TEST 1: Passing whole parse_result (with success, ast, program_name)")
print("-" * 80)
try:
    result = build_cfg_handler({"ast": parse_result})
    print(f"Result: success={result.get('success')}, error={result.get('error')}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 2: Passing an empty dict
print("\n\nTEST 2: Passing empty dict as ast")
print("-" * 80)
try:
    result = build_cfg_handler({"ast": {}})
    print(f"Result: success={result.get('success')}, error={result.get('error')}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 3: Passing a dict with no 'type' field
print("\n\nTEST 3: Passing dict without 'type' field")
print("-" * 80)
try:
    result = build_cfg_handler({"ast": {"program_name": "TEST", "divisions": []}})
    print(f"Result: success={result.get('success')}, error={result.get('error')}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 4: Passing a dict with empty 'type' field
print("\n\nTEST 4: Passing dict with empty 'type' field")
print("-" * 80)
try:
    result = build_cfg_handler({"ast": {"type": "", "program_name": "TEST"}})
    print(f"Result: success={result.get('success')}, error={result.get('error')}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 5: Passing the correct ast
print("\n\nTEST 5: Passing correct AST (should work)")
print("-" * 80)
try:
    result = build_cfg_handler({"ast": parse_result["ast"]})
    print(f"Result: success={result.get('success')}, nodes={result.get('node_count')}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

print("\n" + "=" * 80)

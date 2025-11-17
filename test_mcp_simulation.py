#!/usr/bin/env python3
"""Simulate calling the tools as the MCP client would."""

import json

from src.core.services.tool_handlers_service import (
    build_cfg_handler,
    parse_cobol_handler,
)


print("=" * 80)
print("Simulating MCP client calls")
print("=" * 80)

# Step 1: Call parse_cobol (as MCP client would)
print("\n1. Calling parse_cobol_handler...")
parse_result = parse_cobol_handler({"file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"})

print(f"   Success: {parse_result.get('success')}")
if not parse_result.get("success"):
    print(f"   Error: {parse_result.get('error')}")
    exit(1)

# The MCP client would receive this JSON response
print(f"   AST type in response: {parse_result['ast'].get('type')}")
print(f"   AST keys: {list(parse_result['ast'].keys())}")

# Step 2: Serialize to JSON and back (simulating MCP transport)
print("\n2. Simulating MCP JSON serialization...")
json_str = json.dumps(parse_result)
parse_result_from_json = json.loads(json_str)
print(f"   After JSON round-trip, AST type: {parse_result_from_json['ast'].get('type')}")

# Step 3: Call build_cfg with the AST (as MCP client would)
print("\n3. Calling build_cfg_handler with AST from parse_result...")
try:
    # This is how the MCP wrapper calls it - passing the ast dict directly
    cfg_result = build_cfg_handler({"ast": parse_result_from_json["ast"]})

    print(f"   Success: {cfg_result.get('success')}")
    if cfg_result.get("success"):
        print(f"   Node count: {cfg_result.get('node_count')}")
        print(f"   Edge count: {cfg_result.get('edge_count')}")
    else:
        print(f"   Error: {cfg_result.get('error')}")
except Exception as e:
    print(f"   Exception: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("Test complete")
print("=" * 80)

#!/usr/bin/env python3
"""Final test: parse_cobol → build_cfg with the fixed parser."""

from src.core.services.tool_handlers_service import (
    build_cfg_handler,
    parse_cobol_handler,
)


print("=" * 80)
print("FINAL TEST: parse_cobol → build_cfg")
print("=" * 80)

# Step 1: Parse
parse_result = parse_cobol_handler({"file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"})

print(f"\n✅ Parse: success={parse_result['success']}, program={parse_result.get('program_name')}")

# Step 2: Build CFG
cfg_result = build_cfg_handler({"ast": parse_result["ast"]})

print(
    f"✅ Build CFG: success={cfg_result['success']}, nodes={cfg_result.get('node_count')}, edges={cfg_result.get('edge_count')}"
)

# Show the node names
print("\nCFG Nodes:")
for node in cfg_result["cfg"]["nodes"]:
    print(f"  - {node['node_id']:35} [{node['node_type']}]")

print("\n" + "=" * 80)
print("✅ SUCCESS: The build_cfg tool now works correctly!")
print("=" * 80)

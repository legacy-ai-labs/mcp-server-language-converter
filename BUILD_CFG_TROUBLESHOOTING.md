# build_cfg Tool Troubleshooting Guide

## Error: "ValueError: Unknown AST node type:" (empty string)

### Root Cause
The `build_cfg` tool is receiving an AST dictionary with missing or empty `type` fields on some nodes.

### Common Causes & Solutions

#### 1. Passing the Wrong Data Structure ❌

**WRONG** - Passing the whole `parse_cobol` result:
```json
{
  "success": true,
  "ast": { ... },
  "program_name": "..."
}
```

**CORRECT** - Pass only the `ast` field:
```json
{
  "type": "ProgramNode",
  "program_name": "...",
  "divisions": [...]
}
```

**How to fix in MCP Inspector or Claude Desktop:**
- When calling `build_cfg`, make sure you're passing `result.ast`, not the whole `result`

#### 2. Using Old/Cached AST Data ❌

If you saved an AST from before the parser fixes, it may have issues.

**How to fix:**
1. **Delete any saved AST files**
2. **Restart the MCP server** to get the latest code
3. **Re-run `parse_cobol`** to get a fresh AST
4. **Then run `build_cfg`** with the new AST

#### 3. Parser Not Updated ❌

The parser fixes were made in `src/core/services/cobol_parser_antlr_service.py`.

**How to verify:**
```bash
# Check if the parser has the fixes
grep -A 2 "_extract_value_from_children" src/core/services/cobol_parser_antlr_service.py

# Should see the function definition
```

**How to fix:**
```bash
# Restart the MCP server
# For STDIO mode (Claude Desktop):
# Just restart Claude Desktop

# For HTTP mode:
# Kill the server process and restart it
```

### Testing the Fix

Use this test script to verify everything works:

```bash
uv run python test_final_workflow.py
```

Expected output:
```
✅ Parse: success=True, program=PROGRAM-ID
✅ Build CFG: success=True, nodes=6, edges=5

CFG Nodes:
  - entry                               [EntryNode]
  - exit                                [ExitNode]
  - paragraph_VALIDATE-ACCOUNT-MAIN     [BasicBlock]
  - paragraph_CHECK-CUSTOMER-ID         [BasicBlock]
  - paragraph_CHECK-ACCOUNT-BALANCE     [BasicBlock]
  - paragraph_CHECK-ACCOUNT-STATUS      [BasicBlock]
```

### Correct Usage Example

```python
# Step 1: Parse COBOL
parse_result = parse_cobol({
    "file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"
})

# Step 2: Build CFG from the AST
# ✅ CORRECT: Pass parse_result["ast"]
cfg_result = build_cfg({
    "ast": parse_result["ast"]  # <-- Note: using .ast, not the whole result
})
```

### Improved Error Messages

The code now provides better error messages. If you see:

```
ValueError: AST node missing 'type' field. Available keys: ['success', 'ast', 'program_name']
```

This means you're passing the whole `parse_cobol` result instead of just the `ast` field.

If you see:

```
ValueError: AST node missing 'type' field. Available keys: ['program_name', 'divisions']
```

This means the AST dict is malformed - missing the required `type` field.

### Debug Logging

The handler now logs what it receives:

```python
logger.debug(
    f"build_cfg_handler received ast_dict type={type(ast_dict).__name__}, "
    f"keys={list(ast_dict.keys()) if isinstance(ast_dict, dict) else 'N/A'}"
)
```

Check the logs to see exactly what data is being passed.

### Files for Testing

- `test_final_workflow.py` - End-to-end test (parse → build_cfg)
- `test_mcp_simulation.py` - Simulates MCP client behavior
- `test_wrong_input.py` - Tests various incorrect inputs
- `test_serialization_edge_cases.py` - Tests serialization edge cases

### Summary of Fixes Made

1. **Parser value extraction** - Now recursively searches for terminal nodes
2. **Parser name normalization** - Added `"PARAGRAPHNAME": "PARAGRAPH_NAME"` mapping
3. **Better error messages** - Shows what keys are available when type is missing
4. **Debug logging** - Logs incoming data for troubleshooting

### Still Having Issues?

If you're still getting the error after:
- Restarting the MCP server
- Re-running `parse_cobol` to get a fresh AST
- Verifying you're passing `result.ast` (not the whole result)

Then check:
1. The MCP server logs for the debug output
2. Save the AST to a file and inspect it manually
3. Try running the test scripts to isolate the issue

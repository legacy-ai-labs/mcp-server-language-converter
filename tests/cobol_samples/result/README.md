# COBOL Analysis Tool Results

This directory contains the execution results from COBOL analysis tools. Each tool automatically saves its output to a JSON file in this directory.

## Automated Result Saving

All COBOL analysis tools now automatically save their results to this directory:

- `parse_cobol` - Parses COBOL source into AST
- `parse_cobol_raw` - Parses COBOL into raw parse tree
- `build_ast` - Builds AST from parse tree
- `build_cfg` - Builds Control Flow Graph from AST
- `build_dfg` - Builds Data Flow Graph from AST + CFG
- `build_pdg` - Builds Program Dependency Graph from AST + CFG + DFG

## File Naming Convention

Files are saved with the following pattern:
```
{tool_name}_{program_name}_{timestamp}.json
```

Examples:
- `parse_cobol_ACCOUNT-VALIDATOR_20251122_193045.json`
- `build_cfg_CUSTOMER-ACCOUNT-MAIN_20251122_193050.json`
- `build_pdg_CALCULATE-PENALTY_20251122_193055.json`

## Result Structure

Each result file contains:
- `success`: Boolean indicating if the operation succeeded
- `saved_to`: Path where the result was saved (added automatically)
- Tool-specific data (AST, CFG, DFG, PDG, etc.)
- Metadata (node counts, edge counts, program names, etc.)

### Example: parse_cobol Result

```json
{
  "success": true,
  "ast": {
    "type": "ProgramNode",
    "program_name": "ACCOUNT-VALIDATOR",
    "divisions": [...]
  },
  "program_name": "ACCOUNT-VALIDATOR",
  "saved_to": "tests/cobol_samples/result/parse_cobol_ACCOUNT-VALIDATOR_20251122_193045.json"
}
```

### Example: build_cfg Result

```json
{
  "success": true,
  "cfg": {
    "entry_node": {...},
    "exit_node": {...},
    "nodes": [...],
    "edges": [...]
  },
  "node_count": 15,
  "edge_count": 18,
  "saved_to": "tests/cobol_samples/result/build_cfg_ACCOUNT-VALIDATOR_20251122_193050.json"
}
```

### Example: build_pdg Result

```json
{
  "success": true,
  "pdg": {
    "nodes": [...],
    "edges": [...]
  },
  "node_count": 25,
  "edge_count": 42,
  "control_edge_count": 18,
  "data_edge_count": 24,
  "saved_to": "tests/cobol_samples/result/build_pdg_ACCOUNT-VALIDATOR_20251122_193055.json"
}
```

## Usage via MCP Inspector

When you call any COBOL analysis tool via MCP Inspector:

1. The tool executes and processes the COBOL code
2. The result is automatically saved to this directory
3. The response includes a `saved_to` field with the file path
4. You can review the detailed results in the saved JSON file

## Accessing Results

Results can be accessed:

1. **Via file system**: Browse this directory and open JSON files
2. **Via tool response**: Check the `saved_to` field in the tool's response
3. **Via logs**: Check server logs for "Saved {tool_name} result to..." messages

## File Retention

Files are retained indefinitely unless manually deleted. Consider:
- Archiving old results periodically
- Setting up automated cleanup for files older than X days
- Using version control (git) to track important analysis results

## Error Handling

If result saving fails:
- The tool execution continues normally (saving is non-blocking)
- An error is logged but not returned to the caller
- The `saved_to` field will be absent from the response

Check server logs for:
```
ERROR: Failed to save {tool_name} result: {error_message}
```

## Example Workflow

```bash
# 1. Parse COBOL file
parse_cobol(file_path="tests/cobol_samples/ACCOUNT-VALIDATOR.cbl")
# → Saved to: parse_cobol_ACCOUNT-VALIDATOR_20251122_193045.json

# 2. Build CFG from the AST
build_cfg(ast=<from previous step>)
# → Saved to: build_cfg_ACCOUNT-VALIDATOR_20251122_193050.json

# 3. Build DFG from AST + CFG
build_dfg(ast=<from step 1>, cfg=<from step 2>)
# → Saved to: build_dfg_ACCOUNT-VALIDATOR_20251122_193052.json

# 4. Build PDG from AST + CFG + DFG
build_pdg(ast=<from step 1>, cfg=<from step 2>, dfg=<from step 3>)
# → Saved to: build_pdg_ACCOUNT-VALIDATOR_20251122_193055.json
```

All results are automatically saved and include the complete analysis data for review and debugging.

## Observability Integration

Result saving is integrated with the observability middleware:
- Every tool execution is tracked in the `tool_executions` database table
- Prometheus metrics record execution counts, latency, and errors
- Correlation IDs link database records to saved result files
- Check logs for correlation IDs to trace execution → saved file

Query recent executions:
```sql
SELECT tool_name, status, duration_ms, started_at
FROM tool_executions
WHERE domain = 'cobol_analysis'
ORDER BY started_at DESC
LIMIT 10;
```

# COBOL Analysis MCP Server - Tools Documentation

## Overview

The COBOL Analysis MCP server provides 11 powerful tools for reverse engineering and analyzing COBOL programs.

## Available Tools

### 1. **parse_cobol**
Parse COBOL source code into Abstract Syntax Tree (AST)
- **Args**: `source_code` (string) OR `file_path` (string)
- **Returns**: AST representation of the COBOL program

### 2. **parse_cobol_raw**
Parse COBOL into raw ParseNode (parse tree) without AST transformation
- **Args**: `source_code` (string) OR `file_path` (string)
- **Returns**: Raw parse tree structure

### 3. **build_ast**
Build Abstract Syntax Tree from ParseNode
- **Args**: `parse_tree` (dict)
- **Returns**: Structured AST representation

### 4. **build_cfg**
Build Control Flow Graph (CFG) from AST
- **Args**: `ast` (dict)
- **Returns**: CFG with nodes, edges, and execution paths

### 5. **build_dfg**
Build Data Flow Graph (DFG) from AST and CFG
- **Args**: `ast` (dict), `cfg` (dict)
- **Returns**: DFG showing data dependencies and variable usage

### 6. **build_pdg**
Build Program Dependency Graph (PDG) combining CFG and DFG
- **Args**: `ast` (dict), `cfg` (dict), `dfg` (dict)
- **Returns**: Unified dependency graph for advanced analysis

### 7. **batch_analyze_cobol_directory**
Batch analyze all COBOL files in a directory
- **Args**:
  - `directory_path` (string) - Required
  - `file_extensions` (list[str]) - Optional, defaults to ['.cbl', '.cob', '.cobol']
  - `output_directory` (string) - Optional
- **Returns**: Complete analysis results for all files

### 8. **analyze_program_system** ⭐
Analyze relationships across multiple COBOL programs
- **Args**:
  - `directory_path` (string) - Required
  - `file_extensions` (list[str]) - Optional
  - `include_inactive` (bool) - Default: false
  - `max_depth` (int) - Optional
- **Returns**:
  - `programs` - Program metadata
  - `call_graph` - CALL relationships
  - `copybook_usage` - COPYBOOK dependencies
  - `data_flows` - Parameter passing information
  - `entry_points` - Programs never called by others
  - `isolated_programs` - Programs with no dependencies

### 9. **build_call_graph** ⭐
Build visualization of program CALL relationships
- **Args**:
  - `programs` (dict) - From analyze_program_system
  - `call_graph` (dict) - Optional
  - `output_format` (string) - "dict", "dot", or "mermaid"
  - `include_metrics` (bool) - Default: true
- **Returns**:
  - Graph structure
  - Visualization (for dot/mermaid formats)
  - Metrics (cycles, components, density)

### 10. **analyze_copybook_usage** ⭐
Analyze COPYBOOK sharing patterns
- **Args**:
  - `copybook_usage` (dict) - From analyze_program_system
  - `programs` (dict) - Optional
  - `include_recommendations` (bool) - Default: true
- **Returns**:
  - Copybook analysis
  - Usage statistics
  - Impact analysis
  - Optimization recommendations

### 11. **analyze_data_flow** ⭐
Analyze data flow through program parameters
- **Args**:
  - `data_flows` (list[dict]) - From analyze_program_system
  - `programs` (dict) - Optional
  - `trace_variable` (string) - Optional variable to trace
- **Returns**:
  - Data flow records
  - Flow chains
  - Warnings (mismatches, issues)
  - BY REFERENCE summary

## How to Use with MCP Inspector

### Step 1: Start the HTTP Server (for MCP Inspector)

```bash
cd /Users/hyalen/workspace/mcp-server-language-converter
uv run python -m src.mcp_servers.mcp_cobol_analysis.http_main
```

This will start the server on port **8003**.

### Step 2: Configure MCP Inspector

Use the configuration file `mcp-config-cobol-analysis.json` or configure manually:

```json
{
  "url": "http://localhost:8003/sse",
  "serverName": "COBOL Analysis"
}
```

### Step 3: Test with Sample Data

You can test the inter-program analysis tools with the sample COBOL programs:

```bash
# Run the complete test suite
cd tests/cobol_samples/inter_program_test
uv run python test_inter_program_analysis.py
```

## Example Usage

### Analyze a COBOL Program System

1. Call `analyze_program_system`:
   ```json
   {
     "directory_path": "/path/to/cobol/programs",
     "file_extensions": [".cbl", ".cob"]
   }
   ```

2. Use the results with other tools:
   - `build_call_graph` - Visualize program relationships
   - `analyze_copybook_usage` - Understand shared dependencies
   - `analyze_data_flow` - Track parameter passing

## Typical Workflow

```
1. analyze_program_system(directory)
   ↓
2. build_call_graph(programs, call_graph)
   ↓
3. analyze_copybook_usage(copybook_usage, programs)
   ↓
4. analyze_data_flow(data_flows, programs)
```

## Server Configuration

### STDIO Mode (for Claude Desktop)
```bash
uv run python -m src.mcp_servers.mcp_cobol_analysis
```

### HTTP Streaming Mode (for MCP Inspector)
```bash
uv run python -m src.mcp_servers.mcp_cobol_analysis.http_main
```

Port: **8003**

## Test Data

Sample COBOL programs with relationships are available in:
- **Location**: `tests/cobol_samples/inter_program_test/programs/`
- **Programs**: 11 COBOL programs with CALL relationships
- **Copybooks**: 3 shared copybooks
- **Features**: Circular dependencies, entry points, data flow

## Visualization

The test suite generates:
- `system_analysis.json` - Complete analysis results
- `working_visualization.html` - Interactive graph visualization
- Call graph in DOT and Mermaid formats

Open `tests/cobol_samples/inter_program_test/output/working_visualization.html` to see the interactive visualization!

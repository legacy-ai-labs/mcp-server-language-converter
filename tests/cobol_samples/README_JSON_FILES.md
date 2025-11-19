# COBOL Sample JSON Files

This directory contains serialized AST, CFG, and DFG structures for the ACCOUNT-VALIDATOR-CLEAN.cbl sample program.

## Files

### 1. ACCOUNT-VALIDATOR-CLEAN.cbl
**Source**: Original COBOL program
**Size**: ~2.1 KB
**Purpose**: Sample COBOL account validation program

### 2. ast.json (25 KB)
**Type**: Abstract Syntax Tree
**Created**: 2025-11-17 18:27
**Structure**:
- Program: PROGRAM-ID
- Divisions: 3 (IDENTIFICATION, DATA, PROCEDURE)
- Statements: 23 total
  - MOVE: 11
  - ADD: 3
  - PERFORM: 3
  - IF: 3
  - EVALUATE: 1
  - EXIT: 1
  - DISPLAY: 1

**Usage**:
```python
from test_dfg_from_json import deserialize_program_node
import json

with open("tests/cobol_samples/ast.json") as f:
    ast_data = json.load(f)
ast = deserialize_program_node(ast_data["ast"])
```

### 3. cfg.json (31 KB)
**Type**: Control Flow Graph
**Created**: 2025-11-17 18:29
**Structure**:
- Nodes: 16
  - EntryNode: 1
  - ExitNode: 1
  - BasicBlock: 4 (paragraphs)
  - ControlFlowNode: 10 (IF/PERFORM nodes)
- Edges: 21 (SEQUENTIAL, TRUE, FALSE)

**Usage**:
```python
from test_dfg_from_json import deserialize_control_flow_graph
import json

with open("tests/cobol_samples/cfg.json") as f:
    cfg_data = json.load(f)
cfg = deserialize_control_flow_graph(cfg_data)
```

### 4. dfg.json (6.2 KB) ✨ NEW
**Type**: Data Flow Graph
**Created**: 2025-11-17 18:38
**Structure**:
- Nodes: 20 (all VariableDefNode)
- Edges: 16 (all DEF_USE)
- Variables: 4 unique
  - WS-VALIDATION-RESULT: 6 definitions
  - WS-ERROR-MESSAGE: 6 definitions
  - WS-CHECK-COUNT: 4 definitions
  - LS-VALIDATION-CODE: 4 definitions

**Sample Node**:
```json
{
  "node_type": "VariableDefNode",
  "node_id": "def_WS-VALIDATION-RESULT_0",
  "variable_name": "WS-VALIDATION-RESULT",
  "location": null,
  "statement_type": "StatementType.MOVE"
}
```

**Sample Edge**:
```json
{
  "source_id": "def_LS-VALIDATION-CODE_0",
  "target_id": "def_LS-VALIDATION-CODE_1",
  "edge_type": "DEF_USE"
}
```

**Usage**:
```python
import json

with open("tests/cobol_samples/dfg.json") as f:
    dfg_data = json.load(f)

# Access nodes
for node in dfg_data["nodes"]:
    print(f"{node['node_id']}: {node['variable_name']}")

# Access edges
for edge in dfg_data["edges"]:
    print(f"{edge['source_id']} → {edge['target_id']}")
```

## Variable Definitions in DFG

### WS-VALIDATION-RESULT (6 definitions)
1. `def_WS-VALIDATION-RESULT_0` - MOVE
2. `def_WS-VALIDATION-RESULT_1` - MOVE
3. `def_WS-VALIDATION-RESULT_2` - MOVE
4. `def_WS-VALIDATION-RESULT_3` - MOVE
5. `def_WS-VALIDATION-RESULT_4` - MOVE
6. `def_WS-VALIDATION-RESULT_5` - MOVE

### WS-ERROR-MESSAGE (6 definitions)
1. `def_WS-ERROR-MESSAGE_0` - MOVE
2. `def_WS-ERROR-MESSAGE_1` - MOVE
3. `def_WS-ERROR-MESSAGE_2` - MOVE
4. `def_WS-ERROR-MESSAGE_3` - MOVE
5. `def_WS-ERROR-MESSAGE_4` - MOVE
6. `def_WS-ERROR-MESSAGE_5` - MOVE

### WS-CHECK-COUNT (4 definitions)
1. `def_WS-CHECK-COUNT_0` - MOVE (initialization)
2. `def_WS-CHECK-COUNT_1` - ADD (increment)
3. `def_WS-CHECK-COUNT_2` - ADD (increment)
4. `def_WS-CHECK-COUNT_3` - ADD (increment)

### LS-VALIDATION-CODE (4 definitions)
1. `def_LS-VALIDATION-CODE_0` - MOVE
2. `def_LS-VALIDATION-CODE_1` - MOVE
3. `def_LS-VALIDATION-CODE_2` - MOVE
4. `def_LS-VALIDATION-CODE_3` - MOVE

## Data Flow Chains

### LS-VALIDATION-CODE Flow
```
def_LS-VALIDATION-CODE_0
  ↓ [DEF_USE]
def_LS-VALIDATION-CODE_1
  ↓ [DEF_USE]
def_LS-VALIDATION-CODE_2
  ↓ [DEF_USE]
def_LS-VALIDATION-CODE_3
```

### WS-CHECK-COUNT Flow (Counter Pattern)
```
def_WS-CHECK-COUNT_0 (MOVE - init)
  ↓ [DEF_USE]
def_WS-CHECK-COUNT_1 (ADD - +1)
  ↓ [DEF_USE]
def_WS-CHECK-COUNT_2 (ADD - +1)
  ↓ [DEF_USE]
def_WS-CHECK-COUNT_3 (ADD - +1)
```

### WS-VALIDATION-RESULT Flow
```
def_WS-VALIDATION-RESULT_0
  ↓ [DEF_USE]
def_WS-VALIDATION-RESULT_1
  ↓ [DEF_USE]
def_WS-VALIDATION-RESULT_2
  ↓ [DEF_USE]
def_WS-VALIDATION-RESULT_3
  ↓ [DEF_USE]
def_WS-VALIDATION-RESULT_4
  ↓ [DEF_USE]
def_WS-VALIDATION-RESULT_5
```

### WS-ERROR-MESSAGE Flow
```
def_WS-ERROR-MESSAGE_0
  ↓ [DEF_USE]
def_WS-ERROR-MESSAGE_1
  ↓ [DEF_USE]
def_WS-ERROR-MESSAGE_2
  ↓ [DEF_USE]
def_WS-ERROR-MESSAGE_3
  ↓ [DEF_USE]
def_WS-ERROR-MESSAGE_4
  ↓ [DEF_USE]
def_WS-ERROR-MESSAGE_5
```

## Complete Workflow

To process all three structures:

```python
import json
from test_dfg_from_json import (
    deserialize_program_node,
    deserialize_control_flow_graph,
)

# Load AST
with open("tests/cobol_samples/ast.json") as f:
    ast = deserialize_program_node(json.load(f)["ast"])

# Load CFG
with open("tests/cobol_samples/cfg.json") as f:
    cfg = deserialize_control_flow_graph(json.load(f))

# Load DFG (already JSON - no deserialization needed for simple analysis)
with open("tests/cobol_samples/dfg.json") as f:
    dfg_data = json.load(f)

# Or rebuild DFG from AST/CFG
from src.core.services.dfg_builder_service import build_dfg
dfg = build_dfg(ast, cfg)
```

## Statistics

| File | Type | Size | Nodes | Edges | Created |
|------|------|------|-------|-------|---------|
| ast.json | AST | 25 KB | 23 statements | - | 2025-11-17 |
| cfg.json | CFG | 31 KB | 16 | 21 | 2025-11-17 |
| dfg.json | DFG | 6.2 KB | 20 | 16 | 2025-11-17 |

## Use Cases

### 1. Testing
Use these files as test fixtures for DFG analysis:
```python
def test_dfg_analysis():
    with open("tests/cobol_samples/dfg.json") as f:
        dfg = json.load(f)
    assert len(dfg["nodes"]) == 20
    assert len(dfg["edges"]) == 16
```

### 2. Debugging
Inspect the JSON files to understand the structure:
```bash
cat tests/cobol_samples/dfg.json | jq '.nodes[] | select(.variable_name == "WS-CHECK-COUNT")'
```

### 3. Documentation
Reference these files in documentation to show examples:
```markdown
See `tests/cobol_samples/dfg.json` for a complete DFG example.
```

### 4. API Development
Use as sample responses for API endpoints:
```python
@app.get("/api/dfg/{program_id}")
def get_dfg(program_id: str):
    # Load from cache
    with open(f"cache/{program_id}/dfg.json") as f:
        return json.load(f)
```

## Regeneration

To regenerate any of these files:

```bash
# Regenerate DFG
uv run python save_dfg_to_json.py

# Regenerate AST (if you have the script)
uv run python save_ast_to_json.py

# Regenerate CFG (if you have the script)
uv run python save_cfg_to_json.py
```

## Notes

- All JSON files are human-readable (indented with 2 spaces)
- Files are version controlled in the repository
- DFG only includes VariableDefNode (no VariableUseNode yet)
- All edges are DEF_USE type
- Locations are null (not captured from parser yet)

---

**Last Updated**: 2025-11-17
**COBOL Source**: ACCOUNT-VALIDATOR-CLEAN.cbl
**Parser**: ANTLR-based parser with variable extraction (Steps 2-3 complete)

# COBOL Variable Extraction - Examples and Usage

**Date**: 2025-11-16
**Status**: ✅ Working after Step 3 completion

This document provides comprehensive examples of how variable extraction works in the COBOL analysis system, demonstrating the ANTLR integration improvements made in Steps 2 and 3.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Variable Extraction Basics](#variable-extraction-basics)
3. [Statement-by-Statement Examples](#statement-by-statement-examples)
4. [DFG Analysis Examples](#dfg-analysis-examples)
5. [Complete Workflow Example](#complete-workflow-example)
6. [Advanced Usage](#advanced-usage)

---

## Quick Start

### Minimal Example

```python
from src.core.services.cobol_parser_antlr_service import parse_cobol
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.dfg_builder_service import build_dfg

# Parse COBOL code
cobol_code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. EXAMPLE.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-COUNTER PIC 9(3) VALUE 0.
       PROCEDURE DIVISION.
           MOVE 1 TO WS-COUNTER.
           ADD 1 TO WS-COUNTER.
           STOP RUN.
"""

# Build structures
parsed = parse_cobol(cobol_code)
ast = build_ast(parsed)
cfg = build_cfg(ast)
dfg = build_dfg(ast, cfg)

# Access variables
print(f"DFG has {len(dfg.nodes)} variable definitions")
for node in dfg.nodes:
    print(f"  - {node.variable_name}")
```

**Output**:
```
DFG has 2 variable definitions
  - WS-COUNTER
  - WS-COUNTER
```

---

## Variable Extraction Basics

### How It Works

The variable extraction system uses helper functions to navigate the ANTLR parse tree:

```python
# Helper function: _extract_variable_name()
# Navigates: IDENTIFIER → QUALIFIEDDATANAME → ... → IDENTIFIER (terminal)

identifier_node = _find_child_node(statement, "IDENTIFIER")
variable_name = _extract_variable_name(identifier_node)
# Returns: "WS-COUNTER"
```

### What Gets Extracted

| Statement Type | What's Extracted | Example |
|----------------|------------------|---------|
| MOVE | Source + Target | `MOVE 'Y' TO WS-FLAG` → source='Y', target='WS-FLAG' |
| ADD | Value + Target | `ADD 1 TO WS-COUNT` → value=1, target='WS-COUNT' |
| PERFORM | Target Paragraph | `PERFORM CHECK-ACCOUNT` → target='CHECK-ACCOUNT' |
| IF | Condition + Branches | `IF WS-FLAG = 'Y'` → condition extracted |
| EVALUATE | Expression + WHEN clauses | `EVALUATE WS-STATUS` → expression='WS-STATUS' |

---

## Statement-by-Statement Examples

### 1. MOVE Statement

#### Example 1: Move Literal to Variable

**COBOL Code**:
```cobol
MOVE 'Y' TO WS-VALIDATION-RESULT.
```

**Extraction Process**:
```python
# ANTLR Structure:
# MOVESTATEMENT
#   └─ MOVETOSTATEMENT
#      ├─ MOVETOSENDINGAREA
#      │  └─ LITERAL → NONNUMERICLITERAL = 'Y'
#      └─ IDENTIFIER → ... → 'WS-VALIDATION-RESULT'

# Code extracts:
source = LiteralNode(value='Y', literal_type='STRING')
target = VariableNode(variable_name='WS-VALIDATION-RESULT')
```

**AST Output**:
```python
StatementNode(
    statement_type=StatementType.MOVE,
    attributes={
        'source': LiteralNode(value='Y', literal_type='STRING'),
        'target': VariableNode(variable_name='WS-VALIDATION-RESULT')
    }
)
```

#### Example 2: Move Variable to Variable

**COBOL Code**:
```cobol
MOVE WS-SOURCE-FIELD TO WS-TARGET-FIELD.
```

**Extraction Process**:
```python
# ANTLR Structure:
# MOVESTATEMENT
#   └─ MOVETOSTATEMENT
#      ├─ MOVETOSENDINGAREA
#      │  └─ IDENTIFIER → ... → 'WS-SOURCE-FIELD'
#      └─ IDENTIFIER → ... → 'WS-TARGET-FIELD'

# Code extracts:
source = VariableNode(variable_name='WS-SOURCE-FIELD')
target = VariableNode(variable_name='WS-TARGET-FIELD')
```

#### Example 3: Move Numeric Literal

**COBOL Code**:
```cobol
MOVE ZERO TO WS-CHECK-COUNT.
```

**Extraction Process**:
```python
# ANTLR Structure:
# MOVESTATEMENT
#   └─ MOVETOSTATEMENT
#      ├─ MOVETOSENDINGAREA
#      │  └─ LITERAL → NUMERICLITERAL = 0 (or ZERO keyword)
#      └─ IDENTIFIER → ... → 'WS-CHECK-COUNT'

# Code extracts:
source = LiteralNode(value=0, literal_type='NUMBER')
target = VariableNode(variable_name='WS-CHECK-COUNT')
```

---

### 2. ADD Statement

#### Example 1: Add Numeric Literal

**COBOL Code**:
```cobol
ADD 1 TO WS-CHECK-COUNT.
```

**Extraction Process**:
```python
# ANTLR Structure:
# ADDSTATEMENT
#   └─ ADDTOSTATEMENT
#      ├─ ADDFROM
#      │  └─ LITERAL → NUMERICLITERAL = 1
#      └─ ADDTO
#         └─ IDENTIFIER → ... → 'WS-CHECK-COUNT'

# Code extracts:
value = LiteralNode(value=1, literal_type='NUMBER')
target = VariableNode(variable_name='WS-CHECK-COUNT')
```

**AST Output**:
```python
StatementNode(
    statement_type=StatementType.ADD,
    attributes={
        'value': LiteralNode(value=1, literal_type='NUMBER'),
        'target': VariableNode(variable_name='WS-CHECK-COUNT')
    }
)
```

#### Example 2: Add Variable to Variable

**COBOL Code**:
```cobol
ADD WS-INCREMENT TO WS-TOTAL.
```

**Extraction Process**:
```python
# ANTLR Structure:
# ADDSTATEMENT
#   └─ ADDTOSTATEMENT
#      ├─ ADDFROM
#      │  └─ IDENTIFIER → ... → 'WS-INCREMENT'
#      └─ ADDTO
#         └─ IDENTIFIER → ... → 'WS-TOTAL'

# Code extracts:
value = VariableNode(variable_name='WS-INCREMENT')  # Could be literal or variable
target = VariableNode(variable_name='WS-TOTAL')
```

---

### 3. PERFORM Statement

**COBOL Code**:
```cobol
PERFORM CHECK-CUSTOMER-ID.
```

**Extraction Process**:
```python
# ANTLR Structure:
# PERFORMSTATEMENT
#   └─ PERFORMPROCEDURESTATEMENT
#      └─ PROCEDURENAME
#         └─ PARAGRAPHNAME
#            └─ COBOLWORD
#               └─ IDENTIFIER = 'CHECK-CUSTOMER-ID'

# Code extracts:
target_paragraph = 'CHECK-CUSTOMER-ID'
```

**AST Output**:
```python
StatementNode(
    statement_type=StatementType.PERFORM,
    attributes={
        'target_paragraph': 'CHECK-CUSTOMER-ID'
    }
)
```

---

### 4. IF Statement

#### Example 1: Simple IF

**COBOL Code**:
```cobol
IF VALID-ACCOUNT
    MOVE 'Y' TO WS-VALIDATION-RESULT
END-IF.
```

**Extraction Process**:
```python
# ANTLR Structure:
# IFSTATEMENT
#   ├─ CONDITION → ... → 'VALID-ACCOUNT'
#   └─ IFTHEN
#      └─ STATEMENT
#         └─ MOVESTATEMENT → ...

# Code extracts:
condition = ExpressionNode(...)  # Condition name reference
then_statements = [
    StatementNode(statement_type=MOVE, ...)
]
```

#### Example 2: IF-ELSE

**COBOL Code**:
```cobol
IF WS-VALIDATION-RESULT = 'Y'
    MOVE 'VALID' TO WS-MESSAGE
ELSE
    MOVE 'INVALID' TO WS-MESSAGE
END-IF.
```

**Extraction Process**:
```python
# ANTLR Structure:
# IFSTATEMENT
#   ├─ CONDITION → relational condition
#   ├─ IFTHEN
#   │  └─ STATEMENT → MOVESTATEMENT
#   └─ IFELSE
#      └─ STATEMENT → MOVESTATEMENT

# Code extracts:
condition = ExpressionNode(operator='=', left=..., right=...)
then_statements = [MOVE 'VALID' TO WS-MESSAGE]
else_statements = [MOVE 'INVALID' TO WS-MESSAGE]
```

---

### 5. EVALUATE Statement

**COBOL Code**:
```cobol
EVALUATE LS-ACCOUNT-STATUS
    WHEN 'A'
        CONTINUE
    WHEN 'C'
        MOVE 'CLOSED' TO WS-STATUS-DESC
    WHEN OTHER
        MOVE 'UNKNOWN' TO WS-STATUS-DESC
END-EVALUATE.
```

**Extraction Process**:
```python
# ANTLR Structure:
# EVALUATESTATEMENT
#   ├─ EVALUATESELECT
#   │  └─ IDENTIFIER → 'LS-ACCOUNT-STATUS'
#   ├─ EVALUATEWHENPHRASE (multiple)
#   │  ├─ EVALUATEWHEN → EVALUATECONDITION → EVALUATEVALUE = 'A'
#   │  └─ STATEMENT → CONTINUESTATEMENT
#   └─ EVALUATEWHENOTHER
#      └─ STATEMENT → MOVESTATEMENT

# Code extracts:
expression = VariableNode(variable_name='LS-ACCOUNT-STATUS')
when_clauses = [
    {'value': LiteralNode('A'), 'statements': [...]},
    {'value': LiteralNode('C'), 'statements': [...]}
]
default_statements = [MOVE 'UNKNOWN' TO WS-STATUS-DESC]
```

---

## DFG Analysis Examples

### Example 1: Variable Definition Chain

**COBOL Code**:
```cobol
MOVE 'Y' TO WS-FLAG.
MOVE 'N' TO WS-FLAG.
MOVE 'Y' TO WS-FLAG.
```

**DFG Output**:
```python
# 3 VariableDefNode instances created:
nodes = [
    VariableDefNode(node_id='def_WS-FLAG_0', variable_name='WS-FLAG'),
    VariableDefNode(node_id='def_WS-FLAG_1', variable_name='WS-FLAG'),
    VariableDefNode(node_id='def_WS-FLAG_2', variable_name='WS-FLAG'),
]

# 2 DFG edges showing definition chain:
edges = [
    DFGEdge(source=nodes[0], target=nodes[1], edge_type=DEF_USE),
    DFGEdge(source=nodes[1], target=nodes[2], edge_type=DEF_USE),
]
```

**Visualization**:
```
def_WS-FLAG_0 ('Y')
    ↓ [DEF_USE]
def_WS-FLAG_1 ('N')
    ↓ [DEF_USE]
def_WS-FLAG_2 ('Y')
```

---

### Example 2: Counter Pattern

**COBOL Code**:
```cobol
MOVE ZERO TO WS-COUNT.
ADD 1 TO WS-COUNT.
ADD 1 TO WS-COUNT.
ADD 1 TO WS-COUNT.
```

**DFG Output**:
```python
# 4 VariableDefNode instances:
nodes = [
    VariableDefNode(node_id='def_WS-COUNT_0', variable_name='WS-COUNT'),  # MOVE ZERO
    VariableDefNode(node_id='def_WS-COUNT_1', variable_name='WS-COUNT'),  # ADD 1
    VariableDefNode(node_id='def_WS-COUNT_2', variable_name='WS-COUNT'),  # ADD 1
    VariableDefNode(node_id='def_WS-COUNT_3', variable_name='WS-COUNT'),  # ADD 1
]

# 3 edges:
edges = [
    DFGEdge(source=nodes[0], target=nodes[1], edge_type=DEF_USE),
    DFGEdge(source=nodes[1], target=nodes[2], edge_type=DEF_USE),
    DFGEdge(source=nodes[2], target=nodes[3], edge_type=DEF_USE),
]
```

**Interpretation**:
- Counter initialized to 0
- Incremented 3 times
- Final value (if sequential): 3

---

### Example 3: Multiple Variables

**COBOL Code**:
```cobol
MOVE 'Y' TO WS-RESULT.
MOVE SPACES TO WS-MESSAGE.
ADD 1 TO WS-COUNT.
```

**DFG Output**:
```python
# 3 VariableDefNode instances (different variables):
nodes = [
    VariableDefNode(node_id='def_WS-RESULT_0', variable_name='WS-RESULT'),
    VariableDefNode(node_id='def_WS-MESSAGE_0', variable_name='WS-MESSAGE'),
    VariableDefNode(node_id='def_WS-COUNT_0', variable_name='WS-COUNT'),
]

# No edges (different variables, no data flow between them)
edges = []
```

**Unique Variables**: 3 (WS-RESULT, WS-MESSAGE, WS-COUNT)

---

## Complete Workflow Example

### Real COBOL Program Analysis

**COBOL Code** (from ACCOUNT-VALIDATOR-CLEAN.cbl):
```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCOUNT-VALIDATOR.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-VALIDATION-RESULT  PIC X(1).
       01 WS-ERROR-MESSAGE      PIC X(50).
       01 WS-CHECK-COUNT        PIC 9(3) VALUE 0.

       PROCEDURE DIVISION.
       VALIDATE-ACCOUNT-MAIN.
           MOVE 'Y' TO WS-VALIDATION-RESULT.
           MOVE SPACES TO WS-ERROR-MESSAGE.
           MOVE ZERO TO WS-CHECK-COUNT.

           PERFORM CHECK-CUSTOMER-ID.
           PERFORM CHECK-ACCOUNT-BALANCE.
           PERFORM CHECK-ACCOUNT-STATUS.

           STOP RUN.

       CHECK-CUSTOMER-ID.
           ADD 1 TO WS-CHECK-COUNT.
           IF CUSTOMER-ID = SPACES
               MOVE 'N' TO WS-VALIDATION-RESULT
               MOVE 'CUSTOMER ID IS BLANK' TO WS-ERROR-MESSAGE
           END-IF.
```

### Analysis Script

```python
import sys
sys.path.insert(0, "src")

from src.core.services.cobol_parser_antlr_service import parse_cobol
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.dfg_builder_service import build_dfg

# Read COBOL file
with open("tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl") as f:
    cobol_code = f.read()

# Build all structures
parsed = parse_cobol(cobol_code)
ast = build_ast(parsed)
cfg = build_cfg(ast)
dfg = build_dfg(ast, cfg)

# Analyze variables
print(f"Program: {ast.program_name}")
print(f"CFG: {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")
print(f"DFG: {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")

# Group variables
variables = {}
for node in dfg.nodes:
    var_name = node.variable_name
    if var_name not in variables:
        variables[var_name] = []
    variables[var_name].append(node)

# Show results
print(f"\nVariables found: {len(variables)}")
for var_name in sorted(variables.keys()):
    defs = variables[var_name]
    print(f"  {var_name}: {len(defs)} definitions")
```

### Expected Output

```
Program: PROGRAM-ID
CFG: 16 nodes, 21 edges
DFG: 20 nodes, 16 edges

Variables found: 4
  LS-VALIDATION-CODE: 4 definitions
  WS-CHECK-COUNT: 4 definitions
  WS-ERROR-MESSAGE: 6 definitions
  WS-VALIDATION-RESULT: 6 definitions
```

---

## Advanced Usage

### 1. Extract Variable Values

```python
def get_variable_values(dfg, variable_name):
    """Get all assigned values for a variable."""
    values = []
    for node in dfg.nodes:
        if node.variable_name == variable_name:
            stmt = node.statement
            if stmt.statement_type == StatementType.MOVE:
                source = stmt.attributes.get('source')
                if hasattr(source, 'value'):
                    values.append(source.value)
    return values

# Usage
ws_result_values = get_variable_values(dfg, 'WS-VALIDATION-RESULT')
print(f"WS-VALIDATION-RESULT values: {ws_result_values}")
# Output: ['Y', 'N', 'N', 'N', 'N', 'N']
```

### 2. Find Dead Definitions

```python
def find_dead_definitions(dfg):
    """Find variable definitions that are never used."""
    # Count outgoing edges for each node
    has_use = set()
    for edge in dfg.edges:
        has_use.add(edge.source.node_id)

    # Find nodes with no outgoing edges (except last definition)
    dead = []
    for node in dfg.nodes:
        if node.node_id not in has_use:
            dead.append(node)

    return dead

# Usage
dead_defs = find_dead_definitions(dfg)
for node in dead_defs:
    print(f"Possibly unused: {node.variable_name} at {node.location}")
```

### 3. Trace Variable Flow

```python
def trace_variable_flow(dfg, variable_name):
    """Trace the flow of a variable through definitions."""
    # Get all definitions of this variable
    defs = [n for n in dfg.nodes if n.variable_name == variable_name]

    # Build flow chain using edges
    flow = []
    for i, def_node in enumerate(defs):
        stmt = def_node.statement
        stmt_type = stmt.statement_type

        # Get source value if it's a MOVE
        if stmt_type == StatementType.MOVE:
            source = stmt.attributes.get('source')
            if hasattr(source, 'value'):
                flow.append(f"[{i}] MOVE '{source.value}' TO {variable_name}")
        elif stmt_type == StatementType.ADD:
            value = stmt.attributes.get('value')
            flow.append(f"[{i}] ADD {value.value} TO {variable_name}")

    return flow

# Usage
flow = trace_variable_flow(dfg, 'WS-CHECK-COUNT')
for step in flow:
    print(step)

# Output:
# [0] MOVE '0' TO WS-CHECK-COUNT
# [1] ADD 1 TO WS-CHECK-COUNT
# [2] ADD 1 TO WS-CHECK-COUNT
# [3] ADD 1 TO WS-CHECK-COUNT
```

---

## Troubleshooting

### Common Issues

#### Issue: Variables not extracted

**Symptom**: DFG has 0 nodes

**Solution**: Ensure you're using the updated statement builders from Step 3
```python
# Check if helper functions exist
from src.core.services.ast_builder_service import _extract_variable_name
# This should not raise ImportError
```

#### Issue: Variable names are empty strings

**Symptom**: `variable_name=''` in DFG nodes

**Possible causes**:
1. ANTLR structure different than expected
2. Helper function can't find the terminal IDENTIFIER node

**Debug**:
```python
# Add debug logging in _extract_variable_name()
import logging
logging.basicConfig(level=logging.DEBUG)

# Check the parse tree structure
from src.core.services.cobol_parser_antlr_service import parse_cobol
parsed = parse_cobol(your_code)
# Examine parsed.children to see actual structure
```

---

## Summary

The variable extraction system successfully:

- ✅ Extracts variable names from MOVE, ADD, PERFORM, IF, and EVALUATE statements
- ✅ Handles both literal and variable sources in MOVE statements
- ✅ Creates DFG nodes tracking variable definitions
- ✅ Links definitions with DEF_USE edges showing data flow
- ✅ Supports analysis of real COBOL programs

**Key Files**:
- `src/core/services/ast_builder_service.py` - Statement builders with helper functions
- `src/core/services/dfg_builder_service.py` - DFG generation
- `ANTLR_NODE_MAPPING.md` - ANTLR grammar structure reference
- `STEP3_COMPLETE.md` - Implementation details

**Next Steps**:
- Implement VariableUseNode for read operations
- Add def-use chain analysis
- Support complex expressions
- Implement reaching definitions analysis

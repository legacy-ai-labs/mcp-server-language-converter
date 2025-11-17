# DFG Tool Status Report

## Summary

The `build_dfg` tool returns an empty structure because the **statement attributes don't contain properly formatted variable information** that the DFG builder expects.

## Current Status

### ✅ What's Working

1. **Parse COBOL** - Successfully extracts:
   - ✅ Program name (though generic "PROGRAM-ID")
   - ✅ Divisions (IDENTIFICATION, DATA, PROCEDURE)
   - ✅ Paragraph names (VALIDATE-ACCOUNT-MAIN, CHECK-CUSTOMER-ID, etc.)
   - ✅ **22 statements** across 4 paragraphs

2. **Build CFG** - Successfully builds control flow graph:
   - ✅ 15 nodes (vs 6 before statement parsing)
   - ✅ 23 edges (vs 5 before statement parsing)
   - ✅ Proper paragraph flow representation

3. **Statement Extraction** - Successfully identifies:
   - ✅ 10 MOVE statements
   - ✅ 3 PERFORM statements
   - ✅ 3 IF statements
   - ✅ 3 ADD statements
   - ✅ 1 EVALUATE statement
   - ✅ 1 EXIT statement

### ❌ What's Not Working

**Build DFG** - Returns empty structure (0 nodes, 0 edges)

**Root Cause**: The statement builders create `VariableNode` objects with empty `variable_name` fields because:

1. `_build_move_statement()` looks for nodes named "SOURCE" and "TARGET"
2. But the ANTLR grammar uses different names:
   - **Source**: `MOVETOSENDINGAREA` (not "SOURCE")
   - **Target**: `MOVETORECEIVINGAREA` (not "TARGET")
3. `_find_child_value(node, "SOURCE")` returns `None`
4. Creates `VariableNode(variable_name="")` (empty string)
5. DFG builder's `_variable_name()` returns `None` for empty variable names
6. No variables extracted → No DFG nodes created

##  Fixes Needed

### 1. Update Statement Builders

Each statement builder needs to use the correct ANTLR node names:

**File**: `src/core/services/ast_builder_service.py`

**MOVE Statement** (currently incorrect):
```python
def _build_move_statement(node: ParseNode) -> StatementNode:
    # ❌ WRONG - these nodes don't exist in ANTLR parse tree
    source_name = _find_child_value(node, "SOURCE")
    target_name = _find_child_value(node, "TARGET")
```

**Should be**:
```python
def _build_move_statement(node: ParseNode) -> StatementNode:
    # ✅ CORRECT - use ANTLR grammar node names
    source_name = _find_child_value(node, "MOVETOSENDINGAREA")
    target_name = _find_child_value(node, "MOVETORECEIVINGAREA")
```

### 2. Similar Updates Needed For

- **ADD statement**: Find correct node names for value and target
- **COMPUTE statement**: Find correct node names for expression and target
- **IF statement**: Find correct node names for condition
- **CALL statement**: Find correct node names for parameters
- **PERFORM statement**: Already works (uses PARAGRAPH_NAME which is correct)

### 3. Investigation Steps

For each statement type, need to:

1. Find actual statement in parse tree (like we did for MOVE)
2. Identify the correct child node names
3. Update the corresponding `_build_*_statement` function
4. Add normalization mappings if needed

## Test Results

### Before Statement Parsing Fixes
- AST: 0 statements
- CFG: 6 nodes, 5 edges
- DFG: Empty (expected - no statements)

### After Statement Parsing Fixes
- AST: 22 statements ✅
- CFG: 15 nodes, 23 edges ✅
- DFG: 0 nodes, 0 edges ❌ (statements have empty variable names)

### After Variable Extraction Fixes (not yet implemented)
- AST: 22 statements ✅
- CFG: 15 nodes, 23 edges ✅
- DFG: ~20-30 nodes, ~15-25 edges ✅ (expected - will have variable defs/uses)

## Example: MOVE Statement Fix

**Parse Tree Structure**:
```
MOVESTATEMENT
  ├─ MOVE (keyword)
  └─ MOVETOSTATEMENT
       ├─ MOVETOSENDINGAREA
       │    └─ LITERAL or IDENTIFIER (source variable)
       └─ MOVETORECEIVINGAREA
            └─ IDENTIFIER (target variable)
```

**Current Code** (broken):
```python
source_name = _find_child_value(node, "SOURCE")      # Returns None
target_name = _find_child_value(node, "TARGET")      # Returns None
```

**Fixed Code**:
```python
# Need to navigate: MOVETOSTATEMENT → MOVETOSENDINGAREA → get identifier
sending_area = _find_child_node(node, "MOVETOSENDINGAREA")
receiving_area = _find_child_node(node, "MOVETORECEIVINGAREA")

source_name = _extract_identifier_from_node(sending_area)
target_name = _extract_identifier_from_node(receiving_area)
```

## Next Steps

1. **Investigate each statement type** in the parse tree to find correct node names
2. **Create helper functions** for common patterns (e.g., extracting identifiers)
3. **Update all statement builders** to use correct ANTLR node names
4. **Add comprehensive tests** to verify variable extraction works
5. **Document ANTLR grammar mapping** for future reference

## Files to Update

1. `src/core/services/ast_builder_service.py` - All `_build_*_statement` functions
2. `src/core/services/cobol_parser_antlr_service.py` - Possibly add more normalizations
3. Tests to verify variable extraction works correctly

## Impact

Once fixed, the DFG will:
- ✅ Show variable definitions (where variables are assigned)
- ✅ Show variable uses (where variables are read)
- ✅ Show data flow edges between defs and uses
- ✅ Enable data flow analysis for COBOL programs

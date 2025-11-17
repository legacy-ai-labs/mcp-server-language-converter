# COBOL Statement Structure Investigation - Summary

**Date**: 2025-11-16
**Task**: Step 1 - Investigate each statement type in the parse tree to find correct node names
**Status**: ✅ **COMPLETE**

---

## What Was Done

Created comprehensive documentation of how the ANTLR COBOL grammar structures each statement type in the parse tree.

### Investigation Scripts Created

1. **`investigate_statement_structures.py`**
   - Shows 3-level structure for all statement types
   - Identifies which statements exist in the sample COBOL file
   - Found: MOVE, ADD, PERFORM, IF, EVALUATE, EXIT

2. **`investigate_detailed_structures.py`**
   - Shows 5-level deep structure
   - Traces identifier paths to find variable names
   - Identifies exact node patterns for variable extraction

### Documentation Created

1. **`ANTLR_NODE_MAPPING.md`** ⭐ **PRIMARY REFERENCE**
   - Complete mapping of all statement types
   - Shows correct ANTLR node names vs incorrect current code
   - Provides code examples for each statement type
   - Documents the variable name extraction pattern
   - Includes testing checklist

---

## Key Findings

### Pattern Discovery

**All COBOL variable names follow this path**:
```
IDENTIFIER
  → QUALIFIEDDATANAME
    → QUALIFIEDDATANAMEFORMAT1
      → DATANAME
        → COBOLWORD
          → IDENTIFIER (terminal with actual name)
```

**Current code assumes**:
- Variables have nodes named "SOURCE", "TARGET", "VALUE"
- These don't exist in ANTLR grammar ❌

**Actual ANTLR structure**:
- MOVE uses: `MOVETOSENDINGAREA`, `MOVETOSTATEMENT`, `IDENTIFIER`
- ADD uses: `ADDFROM`, `ADDTO`, `IDENTIFIER`
- PERFORM uses: `PERFORMPROCEDURESTATEMENT`, `PROCEDURENAME`, `PARAGRAPHNAME`

### Statement Counts in Sample File

| Statement Type | Count | Status |
|---|---|---|
| MOVE | 11 | Needs fixing |
| PERFORM | 3 | Needs fixing |
| IF | 3 | Needs fixing |
| ADD | 3 | Needs fixing |
| EVALUATE | 1 | Needs fixing |
| EXIT | 1 | ✅ Working (no params) |
| COMPUTE | 0 | N/A (not in sample) |
| CALL | 0 | N/A (not in sample) |

---

## Impact on DFG

### Why DFG is Empty

1. Statement builders look for wrong node names
2. `_find_child_value(node, "SOURCE")` returns `None`
3. Creates `VariableNode(variable_name="")` (empty)
4. DFG builder's `_variable_name()` rejects empty names
5. No variables extracted → No DFG nodes created

### Expected Results After Fixes

**Current**:
- AST: 22 statements ✅
- CFG: 15 nodes, 23 edges ✅
- DFG: 0 nodes, 0 edges ❌

**After fixes**:
- AST: 22 statements ✅
- CFG: 15 nodes, 23 edges ✅
- DFG: ~20-30 nodes, ~15-25 edges ✅ (expected)

The ACCOUNT-VALIDATOR-CLEAN.cbl file has:
- 11 MOVE statements → ~22 variable operations (source + target)
- 3 ADD statements → ~6 variable operations
- 3 PERFORM statements → not tracked in DFG
- 3 IF conditions → ~3 variable uses
- 1 EVALUATE → ~1 variable use

Expected: **~30 variable def/use nodes** in DFG

---

## Files Created

### Investigation Tools
- `investigate_statement_structures.py` - Basic structure viewer
- `investigate_detailed_structures.py` - Deep structure analysis
- `test_move_statement_structure.py` - MOVE statement inspector

### Documentation
- **`ANTLR_NODE_MAPPING.md`** - Complete mapping reference
- `INVESTIGATION_SUMMARY.md` - This file
- `DFG_STATUS_REPORT.md` - Earlier status report

### Test Utilities (from earlier work)
- `test_dfg_workflow.py` - End-to-end workflow test
- `test_dfg_debug.py` - DFG debugging
- `test_sentence_extraction.py` - Statement extraction test

---

## Next Steps (From Original Plan)

- [x] **Step 1**: Investigate each statement type ✅ **COMPLETE**
- [ ] **Step 2**: Create helper functions for common patterns
- [ ] **Step 3**: Update all statement builders to use correct ANTLR node names
- [ ] **Step 4**: Add comprehensive tests to verify variable extraction works
- [ ] **Step 5**: Document ANTLR grammar mapping for future reference

---

## Usage

**To proceed with fixes**, refer to:
1. **`ANTLR_NODE_MAPPING.md`** - See "Should Be" code for each statement type
2. **Section "Summary of Required Changes"** - Lists all needed helper functions
3. **Section "Files to Update"** - Shows exactly what needs changing

**To test current state**:
```bash
# Run full workflow test
uv run python test_dfg_workflow.py

# Debug specific statement types
uv run python investigate_detailed_structures.py
```

---

## Recommendations

### Approach for Step 2 (Helper Functions)

Create these helper functions first:
1. `_extract_variable_name(identifier_node)` - Most important
2. `_extract_literal_value(literal_node)` - May already exist, verify
3. `_extract_condition(condition_node)` - For IF statements

### Approach for Step 3 (Update Builders)

Update statement builders **one at a time** in this order:
1. **MOVE** - Most common (11 instances), good test case
2. **ADD** - Similar pattern to MOVE
3. **PERFORM** - Different pattern, verify current implementation
4. **IF** - More complex, has nested statements
5. **EVALUATE** - Most complex structure

Test after each statement type is fixed:
```bash
uv run python test_dfg_workflow.py
```

Watch for DFG node count to increase as each statement type is fixed.

---

## Success Criteria

Investigation is complete when:
- [x] All statement types documented
- [x] Variable name extraction pattern identified
- [x] Correct ANTLR node names found for all statement types
- [x] Code examples provided for each fix needed
- [x] Testing approach documented

**Status**: ✅ **ALL CRITERIA MET**

---

## Conclusion

The investigation successfully identified why the DFG is empty and documented exactly what needs to be fixed. The ANTLR grammar uses different node names than the current code expects.

**Key deliverable**: `ANTLR_NODE_MAPPING.md` provides a complete reference for implementing the fixes.

**No code was changed** - maintaining the "don't break what's working" requirement.

Ready to proceed to Step 2 (Create helper functions).

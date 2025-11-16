# Phase 1, Step 9: Pydantic Schemas Implementation

**Status**: ✅ **COMPLETED**

**Date**: 2025-01-27

## Objective

Define Pydantic schemas for COBOL analysis tool input/output validation to ensure type safety and proper validation of tool parameters and responses.

## Implementation Summary

Created comprehensive Pydantic schemas for all three COBOL analysis tools (`parse_cobol`, `build_cfg`, `build_dfg`) with proper validation and type hints.

### Files Created

- `src/core/schemas/cobol_analysis_schema.py` - All COBOL analysis schemas

### Files Modified

- `src/core/schemas/__init__.py` - Added exports for new schemas

## Schemas Implemented

### Request Schemas

1. **`ParseCobolRequest`**
   - Fields: `source_code` (optional), `file_path` (optional)
   - Validation: At least one of `source_code` or `file_path` must be provided
   - Used by: `parse_cobol` tool

2. **`BuildCfgRequest`**
   - Fields: `ast` (required, dict)
   - Used by: `build_cfg` tool

3. **`BuildDfgRequest`**
   - Fields: `ast` (required, dict), `cfg` (required, dict)
   - Used by: `build_dfg` tool

### Response Schemas

1. **`ParseCobolResponse`**
   - Fields: `success` (bool), `ast` (optional dict), `program_name` (optional str), `error` (optional str)
   - Returned by: `parse_cobol` tool

2. **`BuildCfgResponse`**
   - Fields: `success` (bool), `cfg` (optional dict), `node_count` (optional int), `edge_count` (optional int), `error` (optional str)
   - Returned by: `build_cfg` tool

3. **`BuildDfgResponse`**
   - Fields: `success` (bool), `dfg` (optional dict), `node_count` (optional int), `edge_count` (optional int), `error` (optional str)
   - Returned by: `build_dfg` tool

### Nested Structure Schemas

For completeness and future use, also created schemas for nested structures:

**AST Node Schemas**:
- `ASTNodeSchema` (base)
- `ProgramNodeSchema`
- `DivisionNodeSchema`
- `SectionNodeSchema`
- `ParagraphNodeSchema`
- `StatementNodeSchema`
- `ExpressionNodeSchema`
- `VariableNodeSchema`
- `LiteralNodeSchema`

**CFG Schemas**:
- `CFGNodeSchema`
- `CFGEdgeSchema`
- `CFGStructureSchema`

**DFG Schemas**:
- `DFGNodeSchema`
- `DFGEdgeSchema`
- `DFGStructureSchema`

**Common Schemas**:
- `SourceLocationSchema`

## Key Features

### Validation

- **`ParseCobolRequest`** includes a `@model_validator` that ensures at least one input (`source_code` or `file_path`) is provided
- All schemas use Pydantic v2 with proper type hints and field descriptions

### Type Safety

- All schemas use proper Python type hints (`str | None`, `dict[str, Any]`, etc.)
- Response schemas clearly distinguish between success and error cases

### Documentation

- All schemas include descriptive docstrings
- All fields include `description` parameters for better API documentation

## Usage Example

```python
from src.core.schemas import ParseCobolRequest, ParseCobolResponse

# Validate request
request = ParseCobolRequest(source_code="IDENTIFICATION DIVISION.")
# or
request = ParseCobolRequest(file_path="/path/to/file.cbl")

# Validate response
response = ParseCobolResponse(
    success=True,
    ast={"type": "ProgramNode", "program_name": "TEST"},
    program_name="TEST"
)
```

## Integration

The schemas are designed to work with the existing tool handlers in `src/core/services/tool_handlers_service.py`. While the handlers currently accept `dict[str, Any]` for flexibility, these schemas can be used for:

1. **API validation** (when REST API is implemented in Phase 1, Step 10)
2. **Type checking** in development
3. **Documentation** generation
4. **Client SDK** generation

## Testing

Verified schemas work correctly:
- ✅ `ParseCobolRequest` accepts `source_code` or `file_path`
- ✅ `ParseCobolRequest` validation rejects empty input
- ✅ All response schemas accept valid data
- ✅ All schemas import successfully

## Next Steps

These schemas will be used in:
- **Step 10**: REST API implementation (if REST API is added)
- **Future**: Client SDK generation
- **Future**: API documentation generation

## Related Documentation

- [Phase 1 Detailed Plan](COBOL_PHASE1_DETAILED.md)
- [Step 6: Tool Handlers](COBOL_PHASE1_STEP6.md)
- [Step 7: Tool Registration](COBOL_PHASE1_STEP7.md)

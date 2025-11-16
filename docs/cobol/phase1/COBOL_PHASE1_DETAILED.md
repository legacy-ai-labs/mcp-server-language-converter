# Phase 1: Foundation & Parsing - Detailed Implementation Plan

## Overview

Phase 1 establishes the foundational infrastructure for COBOL reverse engineering by implementing core parsing capabilities and graph construction. This phase focuses on building AST, CFG, and DFG from COBOL source code, following the dependency chain: **AST → CFG → DFG**.

**Reference**: See [COBOL Reverse Engineering Plan](../COBOL_REVERSE_ENGINEERING_PLAN.md) for the overall architecture and context.

## Goals

1. **COBOL Parsing**: Parse COBOL source code into structured representation
2. **AST Construction**: Build Abstract Syntax Trees from parsed COBOL
3. **CFG Construction**: Build Control Flow Graphs from AST
4. **DFG Construction**: Build Data Flow Graphs from AST + CFG
5. **MCP Integration**: Expose parsing tools via MCP server

## Deliverables

- COBOL parser integration or custom parser
- AST builder service (`ast_builder.py`)
- CFG builder service (`cfg_builder_service.py`)
- DFG builder service (`dfg_builder_service.py`)
- MCP domain server (`mcp_cobol_analysis`)
- Three MCP tools: `parse_cobol`, `build_cfg`, `build_dfg`
- Unit tests for each component
- Integration tests for full pipeline

## Architecture

### Component Structure

```
src/
├── core/
│   ├── services/
│   │   ├── cobol_parser_service.py          # COBOL parsing logic
│   │   ├── ast_builder_service.py           # AST construction (from parser)
│   │   ├── cfg_builder_service.py           # CFG construction (from AST)
│   │   └── dfg_builder_service.py           # DFG construction (from AST + CFG)
│   ├── models/
│   │   └── cobol_analysis_model.py        # AST/CFG/DFG data models
│   └── schemas/
│       └── cobol_analysis_schema.py        # Pydantic schemas for tool I/O
│
├── mcp_servers/
│   └── mcp_cobol_analysis/
│       ├── __init__.py
│       ├── __main__.py              # STDIO entry point
│       └── http_main.py            # HTTP entry point
```

### Dependency Chain

```
COBOL Source → Parser → AST → CFG → DFG
```

**Critical**: DFG requires CFG to be built first. CFG provides executable paths that DFG uses to track data flow.

## Implementation Steps

### Step 1: COBOL Parser Research & Selection ✅

**Objective**: Identify and integrate a COBOL parser library or build a custom parser.

**Status**: ✅ **COMPLETED**

**Research**: See [COBOL Parser Research](../COBOL_PARSER_RESEARCH.md) for detailed findings and evaluation.

**Implementation**: See [Step 1 Implementation Summary](COBOL_PHASE1_STEP1.md) and [Step 2 Implementation Summary](COBOL_PHASE1_STEP2.md) for implementation details.

**Decision**: PLY-based custom parser selected and implemented.

**Deliverable**: ✅ COBOL parser service (`src/core/services/cobol_parser_service.py`)

---

### Step 2: Data Models for AST/CFG/DFG ✅

**Objective**: Define data structures to represent AST, CFG, and DFG.

**Status**: ✅ **COMPLETED**

**Implementation**: See [Step 2 Implementation Summary](COBOL_PHASE1_STEP2.md) for implementation details.

**Deliverable**: ✅ Data models for AST, CFG, DFG (`src/core/models/cobol_analysis_model.py`)

**Files**:
- `src/core/models/cobol_analysis_model.py` - All data models

**AST Node Types**:
- `ProgramNode` - Root node
- `DivisionNode` - IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE
- `SectionNode` - Sections within divisions
- `ParagraphNode` - Paragraphs within sections
- `StatementNode` - Individual statements (IF, PERFORM, MOVE, etc.)
- `ExpressionNode` - Expressions (conditions, calculations)
- `VariableNode` - Variable references
- `LiteralNode` - Literal values

**CFG Node Types**:
- `BasicBlock` - Sequence of statements with single entry/exit
- `ControlFlowNode` - Represents control flow (IF, PERFORM, GOTO)
- `EntryNode` - Program entry point
- `ExitNode` - Program exit point

**CFG Edge Types**:
- `SequentialEdge` - Normal sequential flow
- `TrueEdge` - True branch of condition
- `FalseEdge` - False branch of condition
- `CallEdge` - PERFORM call to paragraph
- `GotoEdge` - GOTO statement jump

**DFG Node Types**:
- `VariableDefNode` - Variable definition (assignment)
- `VariableUseNode` - Variable use (read)
- `DataFlowNode` - Represents data flow point

**DFG Edge Types**:
- `DefUseEdge` - Definition to use edge
- `UseDefEdge` - Use to definition edge (for transformations)

**Deliverable**: Data models for AST, CFG, DFG

**Files**:
- `src/core/models/cobol_analysis_model.py` - All data models

---

### Step 3: AST Builder Implementation

**Objective**: Build AST from parsed COBOL source.

**Functionality**:
1. Accept parsed COBOL (from parser)
2. Traverse parse tree
3. Build AST nodes for each COBOL construct
4. Preserve hierarchical structure (program → division → section → paragraph → statement)
5. Extract variable references and literals
6. Handle COBOL-specific constructs (PERFORM, GOTO, COPY)

**Key Features**:
- Preserve source location information (line numbers, columns)
- Handle all four COBOL divisions
- Extract data division structures (WORKING-STORAGE, FILE SECTION)
- Map paragraph and section names

**Deliverable**: AST builder service

**Files**:
- `src/core/services/ast_builder_service.py` - AST construction logic
- `docs/cobol/phase1/COBOL_PHASE1_STEP3.md` - Step 3 implementation summary

**Function Signature**:
```python
def build_ast(parsed_cobol: Any) -> ProgramNode:
    """Build AST from parsed COBOL.

    Args:
        parsed_cobol: Parsed COBOL from parser

    Returns:
        ProgramNode representing the AST root
    """
```

---

### Step 4: CFG Builder Implementation

**Objective**: Build CFG from AST, handling COBOL control flow.

**Functionality**:
1. Traverse AST to identify control flow points
2. Build basic blocks (sequences of statements)
3. Create control flow edges:
   - Sequential flow (statement to statement)
   - Conditional branches (IF/EVALUATE true/false)
   - PERFORM calls (call to paragraph, return)
   - GOTO statements (unconditional jumps)
   - Loop structures (PERFORM UNTIL, PERFORM VARYING)
4. Handle paragraph invocations (PERFORM paragraph-name)
5. Resolve paragraph targets for GOTO and PERFORM

**COBOL-Specific Handling**:
- **GOTO**: Create edge to target paragraph
- **PERFORM**: Create call edge to paragraph, return edge after paragraph
- **IF/EVALUATE**: Create true/false branches
- **PERFORM UNTIL/VARYING**: Create loop structures
- **EXIT PROGRAM**: Create exit edge

**Deliverable**: CFG builder service

**Files**:
- `src/core/services/cfg_builder_service.py` - CFG construction logic
- `docs/cobol/phase1/COBOL_PHASE1_STEP4.md` - Step 4 implementation summary

**Function Signature**:
```python
def build_cfg(ast: ProgramNode) -> ControlFlowGraph:
    """Build CFG from AST.

    Args:
        ast: AST root node

    Returns:
        ControlFlowGraph with nodes and edges
    """
```

**Dependencies**: Requires AST to be built first.

---

### Step 5: DFG Builder Implementation

**Objective**: Build DFG from AST + CFG, tracking data flow along executable paths.

**Functionality**:
1. Extract variable definitions from AST (MOVE, COMPUTE, etc.)
2. Extract variable uses from AST (conditions, expressions)
3. Use CFG to determine executable paths
4. Build def-use chains only along CFG paths
5. Track data flow:
   - Variable definitions → uses
   - Data transformations
   - File I/O operations (READ, WRITE)
   - Parameter passing (CALL, PERFORM with USING)

**Key Principle**: Only create data flow edges where CFG shows executable paths.

**Example**:
```cobol
IF BALANCE < 0
    PERFORM APPLY-PENALTY
END-IF
```

- `BALANCE` is read in condition
- Data flow to `APPLY-PENALTY` only along true path (from CFG)
- No data flow along false path

**Deliverable**: DFG builder service

**Files**:
- `src/core/services/dfg_builder_service.py` - DFG construction logic
- `docs/cobol/phase1/COBOL_PHASE1_STEP5.md` - Step 5 implementation summary
- `tests/core/test_dfg_builder.py` - DFG unit tests

**Function Signature**:
```python
def build_dfg(ast: ProgramNode, cfg: ControlFlowGraph) -> DataFlowGraph:
    """Build DFG from AST + CFG.

    Args:
        ast: AST root node (for variable definitions/uses)
        cfg: ControlFlowGraph (for executable paths)

    Returns:
        DataFlowGraph with data flow nodes and edges
    """
```

**Dependencies**: Requires both AST and CFG to be built first.

---

### Step 6: Tool Handlers Implementation

**Objective**: Implement handler functions for MCP tools.

**Tool 1: `parse_cobol`**
- **Input**: COBOL source code (string or file path)
- **Output**: Parsed representation (or AST directly)
- **Handler**: `parse_cobol_handler`

**Tool 2: `build_cfg`**
- **Input**: AST (from `parse_cobol` or AST JSON)
- **Output**: CFG representation (JSON or graph structure)
- **Handler**: `build_cfg_handler`

**Tool 3: `build_dfg`**
- **Input**: AST + CFG (from previous tools)
- **Output**: DFG representation (JSON or graph structure)
- **Handler**: `build_dfg_handler`

**Deliverable**: Tool handlers in `tool_handlers_service.py`

**Files**:
- `src/core/services/tool_handlers_service.py` - Add handlers:
  - `parse_cobol_handler`
  - `build_cfg_handler`
  - `build_dfg_handler`

**Handler Pattern**:
```python
def parse_cobol_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Parse COBOL source code into AST.

    Args:
        parameters: Contains 'source_code' or 'file_path'

    Returns:
        Dictionary with AST representation
    """
    source_code = parameters.get("source_code")
    file_path = parameters.get("file_path")

    # Parse COBOL
    # Build AST
    # Return AST representation

    return {
        "success": True,
        "ast": ast_representation,
    }
```

---

### Step 7: Tool Registration

**Objective**: Register tools in database and create MCP wrappers.

**Database Records** (`scripts/seed_tools.py`):

```python
# Tool 1: parse_cobol
ToolCreate(
    name="parse_cobol",
    description="Parse COBOL source code into Abstract Syntax Tree (AST)",
    handler_name="parse_cobol_handler",
    parameters_schema={
        "type": "object",
        "properties": {
            "source_code": {"type": "string", "description": "COBOL source code"},
            "file_path": {"type": "string", "description": "Path to COBOL file"}
        },
        "required": []
    },
    category="parsing",
    domain="cobol_analysis",
    is_active=True
)

# Tool 2: build_cfg
ToolCreate(
    name="build_cfg",
    description="Build Control Flow Graph (CFG) from AST",
    handler_name="build_cfg_handler",
    parameters_schema={
        "type": "object",
        "properties": {
            "ast": {"type": "object", "description": "AST representation"}
        },
        "required": ["ast"]
    },
    category="parsing",
    domain="cobol_analysis",
    is_active=True
)

# Tool 3: build_dfg
ToolCreate(
    name="build_dfg",
    description="Build Data Flow Graph (DFG) from AST + CFG",
    handler_name="build_dfg_handler",
    parameters_schema={
        "type": "object",
        "properties": {
            "ast": {"type": "object", "description": "AST representation"},
            "cfg": {"type": "object", "description": "CFG representation"}
        },
        "required": ["ast", "cfg"]
    },
    category="parsing",
    domain="cobol_analysis",
    is_active=True
)
```

**MCP Wrappers** (`src/mcp_servers/common/dynamic_loader.py`):

Add wrapper functions for each tool following the existing pattern:

```python
elif tool.name == "parse_cobol":
    async def parse_cobol_tool(
        source_code: str | None = None,
        file_path: str | None = None
    ) -> dict[str, Any]:
        """Parse COBOL source code into AST."""
        async with trace_tool_execution(
            tool_name=tool.name,
            parameters={"source_code": source_code, "file_path": file_path},
            domain=domain,
            transport=transport,
        ) as trace_ctx:
            try:
                result = handler_func({
                    "source_code": source_code,
                    "file_path": file_path
                })
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {e}")
                trace_ctx["status"] = "error"
                trace_ctx["error_type"] = type(e).__name__
                trace_ctx["error_message"] = str(e)
                return {"success": False, "error": str(e)}

            trace_ctx["output_data"] = result
            return result

    decorated_tool = mcp.tool(name=tool.name, description=tool.description)(parse_cobol_tool)
```

**Deliverable**: Tools registered in database and MCP wrappers created

---

### Step 8: MCP Domain Server Creation

**Objective**: Create `mcp_cobol_analysis` domain server following existing pattern.

**Structure**:
```
src/mcp_servers/mcp_cobol_analysis/
├── __init__.py
├── __main__.py              # STDIO entry point
└── http_main.py            # HTTP entry point
```

**`__main__.py`** (STDIO):
```python
"""Entry point for COBOL Analysis MCP server in STDIO mode."""
from src.mcp_servers.common.stdio_runner import run_stdio_server

if __name__ == "__main__":
    run_stdio_server(domain="cobol_analysis")
```

**`http_main.py`** (HTTP):
```python
"""Entry point for COBOL Analysis MCP server in HTTP streaming mode."""
from src.mcp_servers.common.http_runner import run_http_server

if __name__ == "__main__":
    run_http_server(domain="cobol_analysis")
```

**Deliverable**: MCP domain server created (14 lines of code total)

---

### Step 9: Pydantic Schemas

**Objective**: Define schemas for tool input/output validation.

**Schemas**:
- `ParseCobolRequest` - Input for `parse_cobol`
- `ParseCobolResponse` - Output from `parse_cobol`
- `BuildCfgRequest` - Input for `build_cfg`
- `BuildCfgResponse` - Output from `build_cfg`
- `BuildDfgRequest` - Input for `build_dfg`
- `BuildDfgResponse` - Output from `build_dfg`

**Deliverable**: Pydantic schemas for validation

**Files**:
- `src/core/schemas/cobol_analysis_schema.py` - All schemas

---

### Step 10: Testing

**Objective**: Comprehensive testing of all components.

**Unit Tests**:
- Test AST builder with sample COBOL programs
- Test CFG builder with various control flow patterns
- Test DFG builder with data flow scenarios
- Test tool handlers independently

**Integration Tests**:
- Test full pipeline: Parse → AST → CFG → DFG
- Test MCP tool calls end-to-end
- Test error handling (invalid COBOL, missing dependencies)

**Test Cases**:
1. **Simple IF statement** (from example in main plan)
2. **PERFORM paragraph call**
3. **GOTO statement**
4. **File I/O pattern** (READ → PROCESS → WRITE)
5. **Nested conditionals**
6. **Loop structures** (PERFORM UNTIL)

**Deliverable**: Test suite with good coverage

**Files**:
- `tests/core/test_cobol_parser.py`
- `tests/core/test_ast_builder.py`
- `tests/core/test_cfg_builder.py`
- `tests/core/test_dfg_builder.py`
- `tests/mcp_server/test_cobol_analysis_tools.py`

---

## Technical Considerations

### COBOL Parser Selection

**If using existing parser**:
- Wrap parser in service layer
- Normalize output format
- Handle parser-specific quirks

**If building custom parser**:
- Use PLY (Python Lex-Yacc) or similar
- Define COBOL grammar rules
- Handle COBOL's fixed-format vs free-format
- Support common COBOL dialects

### Graph Representation

**Options**:
1. **NetworkX** - Python graph library (recommended)
2. **Custom graph classes** - More control, more work
3. **JSON serialization** - For tool I/O

**Recommendation**: Use NetworkX for internal representation, JSON for tool I/O.

### Performance

- **Caching**: Cache parsed AST/CFG/DFG for repeated analysis
- **Lazy evaluation**: Build graphs on-demand
- **Streaming**: For large programs, consider streaming/chunking

### Error Handling

- **Invalid COBOL**: Return clear error messages
- **Missing dependencies**: CFG requires AST, DFG requires AST+CFG
- **Parser errors**: Handle syntax errors gracefully
- **Graph construction errors**: Handle edge cases (unresolved GOTO targets)

---

## Success Criteria

Phase 1 is complete when:

1. ✅ Can parse COBOL programs into AST
2. ✅ Can build CFG from AST showing control flow
3. ✅ Can build DFG from AST+CFG showing data flow along executable paths
4. ✅ All three tools accessible via MCP (STDIO and HTTP)
5. ✅ Unit tests pass with good coverage (>80%)
6. ✅ Integration tests pass for full pipeline
7. ✅ Handles error cases gracefully
8. ✅ Documentation complete

## Testing Checklist

- [ ] Parse simple COBOL program → AST
- [ ] Build CFG from AST → Control flow graph
- [ ] Build DFG from AST+CFG → Data flow graph
- [ ] Test IF statement (from example)
- [ ] Test PERFORM paragraph call
- [ ] Test GOTO statement
- [ ] Test nested conditionals
- [ ] Test error handling (invalid COBOL)
- [ ] Test MCP tool calls (STDIO)
- [ ] Test MCP tool calls (HTTP)
- [ ] Test dependency chain (DFG requires CFG)

## Dependencies

**External Libraries**:
- COBOL parser (TBD based on research)
- NetworkX (for graph representation)
- FastMCP 2.0 (already in project)
- Pydantic v2 (already in project)

**Internal Dependencies**:
- Database setup (for tool registration)
- MCP server infrastructure (`mcp_servers/common/`)
- Observability system (for tool tracing)

## Next Steps After Phase 1

Once Phase 1 is complete, proceed to:
- **Phase 2**: COBOL-specific analysis (data division, pattern recognition)
- **Phase 3**: Semantic understanding (LLM integration)
- **Phase 4**: Story generation

## References

- [COBOL Reverse Engineering Plan](../COBOL_REVERSE_ENGINEERING_PLAN.md) - Overall plan
- [Architecture Documentation](../ARCHITECTURE.md) - System architecture
- [CLAUDE.md](../../CLAUDE.md) - Development guidelines

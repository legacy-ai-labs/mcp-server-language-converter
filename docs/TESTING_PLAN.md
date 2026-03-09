# MCP Testing & Validation Plan

## Overview

This plan covers thorough testing of all MCP tools, validating tool outputs, reviewing
documentation, and ensuring test coverage across all transport types.

**Baseline file:** `tests/cobol_samples/CALCULATE-PENALTY-CLEAN.cbl` (simple, no copybooks,
no optional paragraphs). More complex files are introduced per phase.

---

## Phase 0 — Baseline Audit

**Goal:** Establish current state before any new work.

- [ ] Run full test suite and record the baseline result:
  ```bash
  uv run pytest --tb=short -q 2>&1 | tee test_baseline.txt
  ```
- [ ] Identify any pre-existing failures. For each failure confirm whether it is related
  to COBOL analysis tools or to unrelated infrastructure.
- [ ] Read the modified documentation files and flag anything that no longer matches the code:
  - `docs/TESTING_QUICKSTART.md`
  - `docs/cobol/COBOL_ANALYSIS_TOOLS_GUIDE.md`

---

## Phase 1 — Tool Validation

**Goal:** Test each tool. Pattern per tool:
1. Run with a known-good input; inspect output structure; verify specific values.
2. Test edge cases (missing params, invalid input, empty program, etc.).

### 1.1`parse_cobol`

- [ ] Input: inline source code of `CALCULATE-PENALTY-CLEAN.cbl` (not a file path)
- [ ] Verify:
  - `success=True`, root node present, `node_count > 0`
  - Output is a raw parse tree (subset of `build_ast` output, without enrichment)
- [ ] Edge cases:
  - Empty string → graceful error, not a crash
  - Invalid syntax (e.g., `IDENTIFICATION GARBAGE.`) → error with descriptive message
  - Non-COBOL text → error with message

### 1.2`prepare_cobol_for_antlr`

- [ ] Input: `tests/cobol_samples/CALCULATE-PENALTY.cbl` (contains `AUTHOR.`, `DATE-WRITTEN.`)
- [ ] Verify:
  - Output source no longer contains `AUTHOR.` or `DATE-WRITTEN.` paragraphs
  - Line count preserved (blank lines substituted, not deleted — so line numbers stay correct)
  - Feed the output directly into `parse_cobol` — must succeed without syntax errors
- [ ] Compare with `CALCULATE-PENALTY-CLEAN.cbl` (manually cleaned) — AST from both
  should be structurally identical
- [ ] Edge cases:
  - File with no optional paragraphs → output identical to input
  - File with all optional paragraphs (AUTHOR, INSTALLATION, DATE-WRITTEN,
    DATE-COMPILED, SECURITY, REMARKS) → all removed

### 1.3`resolve_copybooks`

- [ ] Input: a program that contains `COPY` statements with a copybook directory provided
- [ ] Verify:
  - All COPY statements expanded in output source
  - `copybooks_resolved` list is non-empty
  - Output source parses cleanly via `parse_cobol`
- [ ] Edge cases:
  - Missing copybook directory → error or warning, not crash
  - Non-existent copybook name → appears in `copybooks_missing` list

### 1.4`batch_resolve_copybooks`

- [ ] Input: `tests/cobol_samples/inter_program_test/programs/` with
  `tests/cobol_samples/inter_program_test/copybooks/` as the copybook path
- [ ] Verify:
  - All `.cbl` files processed
  - Each file result shows `success=True`
  - Summary totals match file count
  - No file silently skipped (check `files_failed` list)

### 1.5`build_cfg`

- [ ] Input: `CALCULATE-PENALTY-CLEAN.cbl` (pass AST from `build_ast`)
- [ ] Verify:
  - `success=True`, nodes and edges present
  - `cyclomatic_complexity >= 3` (two nested IFs → at least 3 decision paths)
  - Entry node and at least one exit node present
  - Each paragraph appears as a node
  - Edges connect sequential flow and true/false branches for IF statements
- [ ] Cross-check: paragraph names in CFG nodes match paragraph names from `build_asg`
- [ ] Edge cases:
  - Program with no IFs → `cyclomatic_complexity = 1`
  - Program with PERFORM loops → loop back-edges present in `edges`

### 1.6`build_dfg`

- [ ] Input: `CALCULATE-PENALTY-CLEAN.cbl` (pass AST from `build_ast`)
- [ ] Verify:
  - `success=True`
  - `WS-CALCULATED-PENALTY` has DEF node (COMPUTE statement) and USE nodes (IF condition, MOVE source)
  - `WS-PENALTY-RATE` has USE nodes but no DEF in procedure (initialized by VALUE clause only)
  - Linkage parameters appear as DEF nodes (they are program inputs via USING)
  - No spurious uninitialized-read flags on properly initialized variables
- [ ] Cross-check: variable names in DFG are a subset of `build_asg` data division entry names

### 1.7`analyze_complexity`

- [ ] Input: `CALCULATE-PENALTY-CLEAN.cbl` with `auto_enhance=true`
- [ ] Verify:
  - `cyclomatic_complexity` value matches `build_cfg` result on the same file
  - `lines_of_code > 0`
  - `comment_count` consistent with `build_ast` comment count
- [ ] Test all combinations of optional boolean parameters:

  | `build_asg` | `build_cfg` | `build_dfg` | `auto_enhance` | Expected |
  |:-----------:|:-----------:|:-----------:|:--------------:|:---------|
  | false | false | false | false | AST-level metrics only |
  | true | false | false | false | + ASG metrics (data entries, paragraphs) |
  | false | true | false | false | + CFG metrics (accurate cyclomatic complexity) |
  | false | false | true | false | + DFG metrics (def/use chains, dead vars) |
  | true | true | true | false | Full metrics from all three analyses |
  | false | false | false | true | Auto-selects depth based on complexity score |

### 1.8`build_call_graph`

- [ ] Input: `tests/cobol_samples/inter_program_test/programs/` (run `analyze_program_system`
  first to get the `programs` dict, then pass it to `build_call_graph`)
- [ ] Verify:
  - Entry-point programs have no inbound edges
  - All programs called by others appear as nodes
  - No self-loops unless present in source
  - Graph format `"mermaid"` produces valid Mermaid diagram syntax
- [ ] Cross-check: CALL targets in graph match `build_asg` `call_statements` for each program

### 1.9`analyze_program_system`

- [ ] Input: `tests/cobol_samples/inter_program_test/programs/`
- [ ] Verify:
  - All programs in the directory appear in the system map
  - Inter-program CALL relationships captured
  - Entry points identified (programs that are never called)
  - Leaf programs identified (programs that call no one)
- [ ] Cross-check: relationship data consistent with what `build_call_graph` produces

### 1.10`analyze_copybook_usage`

- [ ] Input: output of `analyze_program_system` on `inter_program_test/`
- [ ] Verify:
  - Each copybook used in the test suite appears in the report
  - Usage count per copybook matches number of programs that include it
  - Each usage entry identifies the program that includes the copybook
  - Unused copybooks (if any) reported separately

### 1.11`analyze_data_flow`

- [ ] Input: `CALCULATE-PENALTY-CLEAN.cbl`, trace variable `WS-CALCULATED-PENALTY`
- [ ] Verify:
  - All assignments to `WS-CALCULATED-PENALTY` identified (COMPUTE statement)
  - All reads identified (IF condition comparison, MOVE source)
  - Data flow trace includes paragraph context for each access
- [ ] Test with linkage variable `LS-PENALTY-AMOUNT` — should show external-facing flow
- [ ] Edge cases:
  - Non-existent variable name → clear error message
  - Variable assigned but never read → flagged as dead variable

### 1.12`batch_analyze_cobol_directory`

- [ ] Input: `tests/cobol_samples/inter_program_test/programs/`
- [ ] Verify:
  - All `.cbl` files processed
  - Each per-file result contains ASG output
  - Summary totals match file count
  - No file silently skipped (check `files_failed` in summary)
- [ ] Cross-check: per-file `program_id` values match the filenames

---

## Phase 2 — Cross-Tool Consistency

**Goal:** Verify that tools which share data agree on the same source.

Run all tools on `CALCULATE-PENALTY-CLEAN.cbl` and check these invariants:

| # | Invariant | Tools involved | Expected |
|---|---|---|---|
| 1 | Node count relationship | `parse_cobol`, `build_ast` | `parse_cobol` count = `build_ast` count + 3 (startRule / compilationUnit / EOF wrapper) |
| 2 | Program name agreement | `build_ast`, `build_asg` | `program_name` identical |
| 3 | Paragraph name agreement | `build_asg`, `build_cfg` | Paragraph names in CFG nodes == paragraph names in ASG |
| 4 | Variable scope | `build_asg`, `build_dfg` | All variable names in DFG declared in ASG data division |
| 5 | Complexity agreement | `build_cfg`, `analyze_complexity` | `cyclomatic_complexity` value identical |
| 6 | Call graph consistency | `build_asg`, `build_call_graph` | CALL targets in call graph == `call_statements` in each program's ASG |
| 7 | Program list consistency | `batch_analyze_cobol_directory`, `build_call_graph` | Same directory → same set of program nodes |

---

## Phase 3 — MCP Transport Testing

**Goal:** Verify all three transports work end-to-end with a real client.

### 3.1 STDIO Transport

- [ ] Start server:
  ```bash
  uv run python -m src.mcp_servers.mcp_cobol_analysis stdio
  ```
- [ ] Connect MCP Inspector: `npx @modelcontextprotocol/inspector`
- [ ] Verify tool list is returned (14 COBOL tools)
- [ ] Call `build_ast` with a `file_path` — verify JSON result returned
- [ ] Call `build_asg` with a `file_path` — verify JSON result returned
- [ ] Call `analyze_complexity` — verify metrics present in response

### 3.2 SSE Transport

- [ ] Start server:
  ```bash
  uv run python -m src.mcp_servers.mcp_cobol_analysis sse
  ```
- [ ] Connect MCP Inspector to `http://localhost:8001/sse`
- [ ] Call `build_asg` with a file path — verify streaming response
- [ ] Call `batch_analyze_cobol_directory` (slow tool) — verify streaming works for long-running calls

### 3.3 Streamable HTTP Transport

- [ ] Start server:
  ```bash
  uv run python -m src.mcp_servers.mcp_cobol_analysis streamable-http
  ```
- [ ] Connect MCP Inspector to `http://localhost:8003/mcp`
- [ ] Call `analyze_complexity` — verify JSON response
- [ ] Call `build_call_graph` with a directory — verify response

### 3.4 Health and Metrics Endpoints

- [ ] `GET http://localhost:9090/health` → `{"status": "ok"}`
- [ ] `GET http://localhost:9090/metrics` → Prometheus format; tool call counters present
- [ ] Call any tool, then re-check metrics — counter for that tool incremented

### 3.5 General Domain Server

- [ ] Start general server:
  ```bash
  uv run python -m src.mcp_servers.mcp_general stdio
  ```
- [ ] Verify general tools are available (`echo`, `calculator_add`, etc.)
- [ ] Confirm COBOL tools are NOT present on the general server

---

## Phase 4 — Documentation Review

**Goal:** Ensure every document matches the current code. Flag outdated content; update
inline or file a note for a follow-up session.

| Document | What to verify |
|---|---|
| `docs/cobol/COBOL_ANALYSIS_TOOLS_GUIDE.md` | Tool signatures, parameter names, output field names, example outputs |
| `docs/TESTING_QUICKSTART.md` | All commands execute as written; ports correct |
| `CLAUDE.md` | Tool list complete; commands accurate; architecture description current |
| `docs/ARCHITECTURE.md` | Hexagonal architecture diagram and description current |
| `docs/DOCKER.md` | Port table matches `docker/docker-compose.yml` |
| `docs/HTTP_STREAMING.md` | SSE connection instructions accurate |
| `docs/STREAMABLE_HTTP.md` | Streamable HTTP instructions accurate |
| `docs/API.md` | API reference matches actual tool signatures |
| `docs/cobol/COBOL_REVERSE_ENGINEERING_PLAN.md` | Completed phases marked done; pending phases still accurate |

For each document:
- [ ] Read the document
- [ ] Run the commands or examples it contains
- [ ] Note any discrepancy between documented and actual behavior
- [ ] Update the document or create a follow-up note

---

## Phase 5 — Test Coverage Gaps

**Goal:** Add automated tests for tools not yet covered. Follow the pattern established in
`tests/core/services/cobol_analysis/test_build_asg.py` (classes grouped by concern).

### Current coverage

| Tool | Test file | Status |
|---|---|---|
| `build_ast` | `tests/core/services/cobol_analysis/test_build_ast.py` | covered |
| `build_asg` | `tests/core/services/cobol_analysis/test_build_asg.py` | covered |
| MCP infrastructure | `tests/mcp_servers/common/` | covered |
| `parse_cobol` | — | missing |
| `prepare_cobol_for_antlr` | — | missing |
| `resolve_copybooks` | — | missing |
| `batch_resolve_copybooks` | — | missing |
| `build_cfg` | — | missing |
| `build_dfg` | — | missing |
| `analyze_complexity` | — | missing |
| `build_call_graph` | — | missing |
| `analyze_program_system` | — | missing |
| `analyze_copybook_usage` | — | missing |
| `analyze_data_flow` | — | missing |
| `batch_analyze_cobol_directory` | — | missing |
| Cross-tool consistency | — | missing |

### New test files to create

```
tests/core/services/cobol_analysis/
├── test_parse_cobol.py
├── test_prepare_cobol_for_antlr.py
├── test_resolve_copybooks.py
├── test_batch_resolve_copybooks.py
├── test_build_cfg.py
├── test_build_dfg.py
├── test_analyze_complexity.py
├── test_build_call_graph.py
├── test_analyze_program_system.py
├── test_analyze_copybook_usage.py
├── test_analyze_data_flow.py
├── test_batch_analyze_cobol_directory.py
└── test_cross_tool_consistency.py   ← integration tests (Phase 3 invariants)
```

### Class structure per test file (example: `test_build_cfg.py`)

```python
class TestBuildCFGBasicFunctionality    # success case, required output fields present
class TestBuildCFGInputValidation        # missing params, invalid types, wrong AST
class TestBuildCFGOutputStructure        # nodes, edges, entry node, exit nodes
class TestBuildCFGCyclomaticComplexity   # specific complexity values for known programs
class TestBuildCFGWithSampleFiles        # CALCULATE-PENALTY, ACCOUNT-VALIDATOR
class TestBuildCFGEdgeCases             # no IFs (CC=1), loops (back-edges), unreachable code
```

### `test_cross_tool_consistency.py` key test cases

```python
def test_node_count_relationship_parse_cobol_vs_build_ast()
def test_program_name_matches_ast_and_asg()
def test_paragraph_names_match_asg_and_cfg()
def test_dfg_variables_subset_of_asg_data_entries()
def test_complexity_cyclomatic_matches_cfg()
def test_call_graph_targets_match_asg_call_statements()
def test_program_list_matches_batch_analyze_and_call_graph()
```

---

## Execution Order

```
Phase 0   Baseline audit — run test suite, read docs
    |
Phase 1   Tool validation (simplest first)
    |     parse_cobol → prepare_cobol_for_antlr → resolve_copybooks → batch_resolve_copybooks
    |     → build_cfg → build_dfg → analyze_complexity
    |     → analyze_program_system → build_call_graph → analyze_copybook_usage
    |     → analyze_data_flow → batch_analyze_cobol_directory
    |
Phase 2   Cross-tool consistency invariants (7 checks)
    |
Phase 3   Transport testing (STDIO, SSE, Streamable HTTP, metrics)
    |
Phase 4   Documentation review (can run in parallel with Phase 1)
    |
Phase 5   Write missing tests (last — informed by all prior findings)
```

---

## Reference: Tool List

| Tool | Phase |
|---|---|
| `parse_cobol` | 1.1 |
| `build_ast` | 1.1 |
| `build_asg` | 1.1 |
| `prepare_cobol_for_antlr` | 1.2 |
| `resolve_copybooks` | 1.3 |
| `batch_resolve_copybooks` | 1.4 |
| `build_cfg` | 1.5 |
| `build_dfg` | 1.6 |
| `analyze_complexity` | 1.7 |
| `build_call_graph` | 1.8 |
| `analyze_program_system` | 1.9 |
| `analyze_copybook_usage` | 1.10 |
| `analyze_data_flow` | 1.11 |
| `batch_analyze_cobol_directory` | 1.12 |

---

## Reference: COBOL Test Files

| File | Characteristics | Best for |
|---|---|---|
| `CALCULATE-PENALTY-CLEAN.cbl` | Simple, no copybooks, nested IFs, 2 paragraphs | Baseline for all tools |
| `CALCULATE-PENALTY.cbl` | Same but with AUTHOR / DATE-WRITTEN paragraphs | `prepare_cobol_for_antlr` |
| `ACCOUNT-VALIDATOR-CLEAN.cbl` | More data fields, validation logic | Data division depth |
| `ACCOUNT-VALIDATOR.cbl` | With optional paragraphs | Preprocessing + AST/ASG |
| `CUSTOMER-ACCOUNT-MAIN.cbl` | Calls sub-programs, ENVIRONMENT DIVISION, FILE SECTION | CFG, call graph |
| `inter_program_test/programs/` | 10 programs calling each other + 3 copybooks | System-level tools |

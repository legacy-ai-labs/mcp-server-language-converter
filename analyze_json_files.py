"""Comprehensive analysis of AST, CFG, and DFG JSON files."""

import json
from collections import defaultdict


print("=" * 80)
print("COMPREHENSIVE ANALYSIS OF AST, CFG, AND DFG")
print("=" * 80)
print()

# Load all three files
with open("tests/cobol_samples/ast.json") as f:
    ast_data = json.load(f)

with open("tests/cobol_samples/cfg.json") as f:
    cfg_data = json.load(f)

with open("tests/cobol_samples/dfg.json") as f:
    dfg_data = json.load(f)

# ============================================================================
# AST ANALYSIS
# ============================================================================
print("1. AST ANALYSIS")
print("-" * 80)

ast = ast_data["ast"]
procedure_div = [d for d in ast["divisions"] if d["division_type"] == "PROCEDURE"][0]
paragraphs = procedure_div["sections"][0]["paragraphs"]

print(f"Program: {ast['program_name']}")
print(f"Divisions: {len(ast['divisions'])}")
print(f"Paragraphs: {len(paragraphs)}")
print()

# Count statements by paragraph
for para in paragraphs:
    stmt_types = defaultdict(int)
    for stmt in para["statements"]:
        stmt_types[stmt["statement_type"]] += 1
    print(f"  {para['paragraph_name']}:")
    for stype, count in sorted(stmt_types.items()):
        print(f"    - {stype}: {count}")

# Extract PERFORM targets from AST
print("\n  PERFORM Targets (from AST):")
perform_targets = []
for para in paragraphs:
    for stmt in para["statements"]:
        if stmt["statement_type"] == "PERFORM":
            target = stmt["attributes"]["target_paragraph"]
            perform_targets.append(target)
            print(f"    - {target}")

print()

# ============================================================================
# CFG ANALYSIS
# ============================================================================
print("2. CFG ANALYSIS")
print("-" * 80)

cfg_nodes = cfg_data["nodes"]
cfg_edges = cfg_data["edges"]

node_types = defaultdict(int)
for node in cfg_nodes:
    node_types[node["node_type"]] += 1

print(f"Total Nodes: {len(cfg_nodes)}")
for ntype, count in sorted(node_types.items()):
    print(f"  - {ntype}: {count}")

print(f"\nTotal Edges: {len(cfg_edges)}")
edge_types = defaultdict(int)
for edge in cfg_edges:
    edge_types[edge["edge_type"]] += 1
for etype, count in sorted(edge_types.items()):
    print(f"  - {etype}: {count}")

# Check PERFORM edges
print("\n  PERFORM Edges:")
perform_edges = [e for e in cfg_edges if e["edge_type"] == "CALL"]
for edge in perform_edges:
    source = next(n for n in cfg_nodes if n["node_id"] == edge["source_id"])
    target = next(n for n in cfg_nodes if n["node_id"] == edge["target_id"])
    print(f"    {source['label']} -> {target['label']}")

# Check IF branches
print("\n  IF Branch Edges:")
if_edges = [(e, e["edge_type"]) for e in cfg_edges if e["edge_type"] in ["TRUE", "FALSE"]]
for edge, etype in if_edges:
    source = next(n for n in cfg_nodes if n["node_id"] == edge["source_id"])
    target = next(n for n in cfg_nodes if n["node_id"] == edge["target_id"])
    print(f"    {source['label']} -> {target['label']} ({etype})")

print()

# ============================================================================
# DFG ANALYSIS
# ============================================================================
print("3. DFG ANALYSIS")
print("-" * 80)

dfg_nodes = dfg_data["nodes"]
dfg_edges = dfg_data["edges"]

print(f"Total Nodes: {len(dfg_nodes)}")
print(f"Total Edges: {len(dfg_edges)}")

# Group by variable
variables = defaultdict(list)
for node in dfg_nodes:
    variables[node["variable_name"]].append(node)

print(f"\nVariables tracked: {len(variables)}")
for var_name in sorted(variables.keys()):
    nodes = variables[var_name]
    print(f"  - {var_name}: {len(nodes)} definitions")

# Check for IF branch issues
print("\n  IF Branch Edge Check:")
print("  Looking for LS-VALIDATION-CODE edges...")
ls_edges = [
    e
    for e in dfg_edges
    if any(
        n["node_id"] == e["source_id"] and "LS-VALIDATION-CODE" in n["variable_name"]
        for n in dfg_nodes
    )
]

for edge in ls_edges:
    print(f"    {edge['source_id']} -> {edge['target_id']}")

# Check for incorrect branch edges
print("\n  Checking for incorrect edges between THEN (_0) and ELSE (_1):")
incorrect_edges = []
for edge in dfg_edges:
    if (
        edge["source_id"].endswith("_0")
        and edge["target_id"].endswith("_1")
        and "LS-VALIDATION-CODE" in edge["source_id"]
    ):
        incorrect_edges.append(edge)

if incorrect_edges:
    print("  ❌ FOUND INCORRECT EDGES:")
    for edge in incorrect_edges:
        print(f"    {edge['source_id']} -> {edge['target_id']}")
else:
    print("  ✅ No incorrect edges between IF branches")

print()

# ============================================================================
# CROSS-FILE VERIFICATION
# ============================================================================
print("4. CROSS-FILE VERIFICATION")
print("-" * 80)

# Verify PERFORM targets match
print("✓ Verifying PERFORM targets...")
ast_perform_targets = set(perform_targets)
cfg_perform_targets = set()
for node in cfg_nodes:
    if node.get("control_type") == "PERFORM" and node.get("target_paragraph"):
        cfg_perform_targets.add(node["target_paragraph"])

if ast_perform_targets == cfg_perform_targets:
    print(f"  ✅ PERFORM targets match: {sorted(ast_perform_targets)}")
else:
    print("  ❌ MISMATCH!")
    print(f"     AST: {sorted(ast_perform_targets)}")
    print(f"     CFG: {sorted(cfg_perform_targets)}")

# Verify paragraph nodes exist in CFG
print("\n✓ Verifying paragraph nodes...")
ast_paragraphs = set(p["paragraph_name"] for p in paragraphs)
cfg_paragraphs = set()
for node in cfg_nodes:
    if node.get("node_type") == "BasicBlock" and node["node_id"].startswith("paragraph_"):
        cfg_paragraphs.add(node["label"])

if ast_paragraphs == cfg_paragraphs:
    print(f"  ✅ All {len(ast_paragraphs)} paragraphs exist in CFG")
else:
    print("  ❌ MISMATCH!")
    print(f"     AST has: {sorted(ast_paragraphs)}")
    print(f"     CFG has: {sorted(cfg_paragraphs)}")

# Verify variables in DFG come from AST
print("\n✓ Verifying variables...")
ast_variables = set()
for para in paragraphs:
    for stmt in para["statements"]:
        # Extract target variables from MOVE and ADD statements
        if stmt["statement_type"] in ["MOVE", "ADD"]:
            if "target" in stmt["attributes"]:
                target = stmt["attributes"]["target"]
                if isinstance(target, dict) and "variable_name" in target:
                    ast_variables.add(target["variable_name"])
        # Check nested statements in IF
        if stmt["statement_type"] == "IF":
            for branch in ["then_statements", "else_statements"]:
                if branch in stmt["attributes"]:
                    for nested_stmt in stmt["attributes"][branch]:
                        if "target" in nested_stmt["attributes"]:
                            target = nested_stmt["attributes"]["target"]
                            if isinstance(target, dict) and "variable_name" in target:
                                ast_variables.add(target["variable_name"])

dfg_variables = set(var_name for var_name in variables.keys())

if dfg_variables.issubset(ast_variables):
    print(f"  ✅ All {len(dfg_variables)} DFG variables exist in AST")
    print(f"     Variables: {sorted(dfg_variables)}")
else:
    missing = dfg_variables - ast_variables
    print(f"  ⚠️  Some DFG variables not found in AST: {missing}")

print()

# ============================================================================
# CORRECTNESS CHECKS
# ============================================================================
print("5. CORRECTNESS CHECKS")
print("-" * 80)

issues = []

# Check 1: PERFORM targets are not empty
empty_performs = [
    node
    for node in cfg_nodes
    if node.get("control_type") == "PERFORM" and not node.get("target_paragraph")
]
if empty_performs:
    issues.append(f"❌ Found {len(empty_performs)} PERFORM nodes with empty targets")
else:
    print("✅ All PERFORM nodes have valid targets")

# Check 2: All PERFORM targets exist as paragraphs
missing_targets = []
for target in cfg_perform_targets:
    if target not in cfg_paragraphs:
        missing_targets.append(target)
if missing_targets:
    issues.append(f"❌ PERFORM targets not found as paragraphs: {missing_targets}")
else:
    print("✅ All PERFORM targets exist as paragraphs")

# Check 3: CFG is connected
reachable = set()
to_visit = [cfg_data["entry_node"]["node_id"]]
while to_visit:
    current = to_visit.pop()
    if current in reachable:
        continue
    reachable.add(current)
    for edge in cfg_edges:
        if edge["source_id"] == current:
            to_visit.append(edge["target_id"])

unreachable = set(n["node_id"] for n in cfg_nodes) - reachable
if unreachable:
    issues.append(f"⚠️  {len(unreachable)} unreachable CFG nodes: {unreachable}")
else:
    print("✅ All CFG nodes are reachable from entry")

# Check 4: DFG edges are valid
invalid_dfg_edges = []
node_ids = set(n["node_id"] for n in dfg_nodes)
for edge in dfg_edges:
    if edge["source_id"] not in node_ids or edge["target_id"] not in node_ids:
        invalid_dfg_edges.append(edge)
if invalid_dfg_edges:
    issues.append(f"❌ {len(invalid_dfg_edges)} invalid DFG edges (dangling references)")
else:
    print("✅ All DFG edges reference valid nodes")

# Check 5: No self-loops in DFG (except for CALL/RETURN in CFG)
self_loops = [e for e in dfg_edges if e["source_id"] == e["target_id"]]
if self_loops:
    issues.append(f"⚠️  {len(self_loops)} DFG self-loops: {self_loops}")
else:
    print("✅ No DFG self-loops")

print()

if issues:
    print("⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("✅ ALL CHECKS PASSED!")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(
    f"AST: {len(paragraphs)} paragraphs, {sum(len(p['statements']) for p in paragraphs)} statements"
)
print(f"CFG: {len(cfg_nodes)} nodes, {len(cfg_edges)} edges")
print(f"DFG: {len(dfg_nodes)} variable definitions, {len(dfg_edges)} def-use edges")
print(f"Files are {'✅ CORRECT' if not issues else '⚠️ HAVE ISSUES'} and properly related")
print("=" * 80)

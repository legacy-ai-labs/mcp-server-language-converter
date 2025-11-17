#!/usr/bin/env python3
"""Debug DFG building."""

import logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

from src.core.services.cobol_parser_antlr_service import parse_cobol_file
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.dfg_builder_service import build_dfg

print("=" * 80)
print("DFG Building Debug Test")
print("=" * 80)

# Parse and build AST
print("\n1. Parsing and building AST...")
parsed_tree = parse_cobol_file("tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl")
ast = build_ast(parsed_tree)

# Check statements
total_stmts = 0
for div in ast.divisions:
    if div.division_type.value == "PROCEDURE":
        for section in div.sections:
            for para in section.paragraphs:
                print(f"   {para.paragraph_name}: {len(para.statements)} statements")
                for i, stmt in enumerate(para.statements):
                    print(f"      [{i+1}] {stmt.statement_type.value}: {list(stmt.attributes.keys())}")
                    total_stmts += 1

print(f"\n   Total statements: {total_stmts}")

# Build CFG
print("\n2. Building CFG...")
cfg = build_cfg(ast)
print(f"   CFG: {len(cfg.nodes)} nodes, {len(cfg.edges)} edges")

# Build DFG
print("\n3. Building DFG...")
try:
    dfg = build_dfg(ast, cfg)
    print(f"   DFG: {len(dfg.nodes)} nodes, {len(dfg.edges)} edges")

    if len(dfg.nodes) == 0:
        print("\n   ⚠️  DFG is empty - checking why...")
        print("   This usually means statements don't have variable definitions or uses")
        print("   that the DFG builder recognizes.")
except Exception as e:
    print(f"   ❌ Error building DFG: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

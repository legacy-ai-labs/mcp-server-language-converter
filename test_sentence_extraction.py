#!/usr/bin/env python3
"""Test if SENTENCE nodes are being found."""

from src.core.services.cobol_parser_antlr_service import parse_cobol_file
from src.core.services.ast_builder_service import build_ast, _walk_nodes

print("=" * 80)
print("Testing SENTENCE node extraction")
print("=" * 80)

# Parse the file
print("\n1. Parsing COBOL file...")
parsed_tree = parse_cobol_file("tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl")
print(f"   Root node type: {parsed_tree.node_type}")

# Build AST
print("\n2. Building AST...")
ast = build_ast(parsed_tree)
print(f"   Program name: {ast.program_name}")

# Find procedure division
print("\n3. Looking for PROCEDURE division...")
procedure_div = None
for div in ast.divisions:
    if div.division_type.value == "PROCEDURE":
        procedure_div = div
        print(f"   Found PROCEDURE division with {len(div.sections)} sections")
        break

if procedure_div:
    for section in procedure_div.sections:
        print(f"\n4. Section: {section.section_name}")
        print(f"   Paragraphs: {len(section.paragraphs)}")

        for para in section.paragraphs:
            print(f"\n   Paragraph: {para.paragraph_name}")
            print(f"     Statements: {len(para.statements)}")

            # Now let's check the parsed tree directly
            # We need to find corresponding ParseNode
            print(f"     Checking raw parse tree for SENTENCE nodes...")

# Let's check the parsed_tree directly
print("\n\n5. Direct check of parsed tree for SENTENCE nodes:")
print("-" * 80)

def count_nodes_by_type(node, target_type):
    """Count nodes of a specific type."""
    count = 0
    if hasattr(node, 'node_type') and node.node_type == target_type:
        count = 1
    if hasattr(node, 'children'):
        for child in node.children:
            count += count_nodes_by_type(child, target_type)
    return count

sentence_count = count_nodes_by_type(parsed_tree, "SENTENCE")
statement_count = count_nodes_by_type(parsed_tree, "STATEMENT")
move_count = count_nodes_by_type(parsed_tree, "MOVE_STATEMENT")
perform_count = count_nodes_by_type(parsed_tree, "PERFORM_STATEMENT")

print(f"SENTENCE nodes in parse tree: {sentence_count}")
print(f"STATEMENT nodes in parse tree: {statement_count}")
print(f"MOVE_STATEMENT nodes in parse tree: {move_count}")
print(f"PERFORM_STATEMENT nodes in parse tree: {perform_count}")

print("\n" + "=" * 80)

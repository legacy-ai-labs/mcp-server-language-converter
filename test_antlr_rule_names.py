#!/usr/bin/env python3
"""Check what rule names ANTLR is actually producing."""

from antlr4 import CommonTokenStream, FileStream

from src.core.services.antlr_cobol.grammars.Cobol85Lexer import Cobol85Lexer
from src.core.services.antlr_cobol.grammars.Cobol85Parser import Cobol85Parser


file_path = "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"

# Parse the file
input_stream = FileStream(file_path)
lexer = Cobol85Lexer(input_stream)
token_stream = CommonTokenStream(lexer)
parser = Cobol85Parser(token_stream)
tree = parser.startRule()


def collect_rule_names(node, parser_instance, depth=0, max_depth=10):
    """Collect all rule names in the tree."""
    if depth > max_depth:
        return []

    results = []

    # Check if it's a rule context (not a terminal)
    if hasattr(node, "getRuleIndex"):
        rule_index = node.getRuleIndex()
        rule_name = parser_instance.ruleNames[rule_index]
        results.append(
            {
                "depth": depth,
                "rule_name": rule_name,
                "rule_index": rule_index,
                "children_count": len(node.children) if node.children else 0,
            }
        )

        # Recurse into children
        if node.children:
            for child in node.children:
                results.extend(collect_rule_names(child, parser_instance, depth + 1, max_depth))

    return results


print("Collecting rule names from ANTLR parse tree...")
print("=" * 80)

rule_names = collect_rule_names(tree, parser)

# Find paragraph-related rules
print("\nParagraph-related rules:")
print("=" * 80)
paragraph_rules = [r for r in rule_names if "paragraph" in r["rule_name"].lower()]
for rule in paragraph_rules[:20]:
    indent = "  " * rule["depth"]
    print(
        f"{indent}{rule['rule_name']} (index={rule['rule_index']}, children={rule['children_count']})"
    )

print("\n" + "=" * 80)
print("\nProgram name rules:")
print("=" * 80)
program_rules = [
    r
    for r in rule_names
    if "program" in r["rule_name"].lower() and "name" in r["rule_name"].lower()
]
for rule in program_rules[:10]:
    indent = "  " * rule["depth"]
    print(
        f"{indent}{rule['rule_name']} (index={rule['rule_index']}, children={rule['children_count']})"
    )

print("\n" + "=" * 80)
print("\nUnique rule names containing 'Name':")
print("=" * 80)
name_rules = set([r["rule_name"] for r in rule_names if "Name" in r["rule_name"]])
for rule_name in sorted(name_rules):
    print(f"  - {rule_name}")

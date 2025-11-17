#!/usr/bin/env python3
"""Debug value extraction in the parser."""

from antlr4 import FileStream, CommonTokenStream
from antlr4.tree.Tree import TerminalNode
from src.core.services.antlr_cobol.grammars.Cobol85Lexer import Cobol85Lexer
from src.core.services.antlr_cobol.grammars.Cobol85Parser import Cobol85Parser

file_path = "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"

# Parse the file
input_stream = FileStream(file_path)
lexer = Cobol85Lexer(input_stream)
token_stream = CommonTokenStream(lexer)
parser = Cobol85Parser(token_stream)
tree = parser.startRule()

def find_paragraph_names(node, parser_instance, depth=0):
    """Find all paragraphName nodes and check their children."""
    results = []

    if hasattr(node, 'getRuleIndex'):
        rule_index = node.getRuleIndex()
        rule_name = parser_instance.ruleNames[rule_index]

        if rule_name == 'paragraphName':
            result = {
                'depth': depth,
                'rule_name': rule_name,
                'children': []
            }

            # Check children
            if node.children:
                for child in node.children:
                    if isinstance(child, TerminalNode):
                        symbol = child.getSymbol()
                        token_type = parser_instance.symbolicNames[symbol.type] if symbol.type < len(parser_instance.symbolicNames) else "UNKNOWN"
                        result['children'].append({
                            'type': 'Terminal',
                            'token_type': token_type,
                            'value': symbol.text
                        })
                    elif hasattr(child, 'getRuleIndex'):
                        child_rule = parser_instance.ruleNames[child.getRuleIndex()]
                        result['children'].append({
                            'type': 'Rule',
                            'rule_name': child_rule,
                            'child_count': len(child.children) if child.children else 0
                        })

            results.append(result)

        # Recurse
        if node.children:
            for child in node.children:
                results.extend(find_paragraph_names(child, parser_instance, depth + 1))

    return results

print("Finding paragraphName nodes and their children...")
print("=" * 80)

paragraph_names = find_paragraph_names(tree, parser)

for i, pname in enumerate(paragraph_names):
    print(f"\n[{i+1}] paragraphName node:")
    print(f"     Children count: {len(pname['children'])}")
    for child in pname['children']:
        if child['type'] == 'Terminal':
            print(f"       - Terminal: {child['token_type']} = '{child['value']}'")
        else:
            print(f"       - Rule: {child['rule_name']} ({child['child_count']} children)")

print("\n" + "=" * 80)
print("This shows what children each paragraphName node has")
print("The parser should extract values from Terminal children")

#!/usr/bin/env python3
"""Investigate why the parser is producing generic output."""

import json
from src.core.services.tool_handlers_service import parse_cobol_handler

print("Testing parser with ACCOUNT-VALIDATOR-CLEAN.cbl")
print("=" * 80)

result = parse_cobol_handler({
    "file_path": "tests/cobol_samples/ACCOUNT-VALIDATOR-CLEAN.cbl"
})

print(f"Success: {result.get('success')}")
print(f"Program name: {result.get('program_name')}")

if result.get('success'):
    ast = result['ast']

    # Check PROCEDURE division
    for division in ast.get('divisions', []):
        if division.get('division_type') == 'PROCEDURE':
            print(f"\nPROCEDURE Division found:")
            print(f"  Sections: {len(division.get('sections', []))}")

            for section in division.get('sections', []):
                print(f"\n  Section: {section.get('section_name')}")
                paragraphs = section.get('paragraphs', [])
                print(f"    Paragraphs: {len(paragraphs)}")

                for i, para in enumerate(paragraphs):
                    para_name = para.get('paragraph_name')
                    statements = para.get('statements', [])
                    print(f"      [{i+1}] {para_name} - {len(statements)} statements")

                    if statements:
                        print(f"          First statement type: {statements[0].get('statement_type')}")

print("\n" + "=" * 80)
print("Expected paragraphs from COBOL file:")
print("  - VALIDATE-ACCOUNT-MAIN")
print("  - CHECK-CUSTOMER-ID")
print("  - CHECK-ACCOUNT-BALANCE")
print("  - CHECK-ACCOUNT-STATUS")
print("\n" + "=" * 80)

# Save full AST for inspection
with open("parser_investigation_output.json", "w") as f:
    json.dump(result, f, indent=2)

print("Full AST saved to: parser_investigation_output.json")

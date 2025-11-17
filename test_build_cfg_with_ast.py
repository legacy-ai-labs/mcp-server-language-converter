#!/usr/bin/env python3
"""Test build_cfg with the specific AST that failed."""

import json
from src.core.services.tool_handlers_service import build_cfg_handler

# The exact AST provided by the user
ast_data = {
    "type": "ProgramNode",
    "program_name": "PROGRAM-ID",
    "divisions": [
        {
            "type": "DivisionNode",
            "division_type": "IDENTIFICATION",
            "sections": [
                {
                    "type": "SectionNode",
                    "section_name": "PROGRAM-ID",
                    "paragraphs": [
                        {
                            "type": "ParagraphNode",
                            "paragraph_name": "PROGRAM-ID",
                            "statements": [
                                {
                                    "type": "StatementNode",
                                    "statement_type": "DISPLAY",
                                    "attributes": {
                                        "program_id": "PROGRAM-ID"
                                    },
                                    "location": None
                                }
                            ],
                            "location": None
                        }
                    ],
                    "location": None
                }
            ],
            "location": None
        },
        {
            "type": "DivisionNode",
            "division_type": "DATA",
            "sections": [],
            "location": None
        },
        {
            "type": "DivisionNode",
            "division_type": "PROCEDURE",
            "sections": [
                {
                    "type": "SectionNode",
                    "section_name": "PROCEDURE",
                    "paragraphs": [
                        {
                            "type": "ParagraphNode",
                            "paragraph_name": "PARAGRAPH",
                            "statements": [],
                            "location": None
                        },
                        {
                            "type": "ParagraphNode",
                            "paragraph_name": "PARAGRAPH",
                            "statements": [],
                            "location": None
                        },
                        {
                            "type": "ParagraphNode",
                            "paragraph_name": "PARAGRAPH",
                            "statements": [],
                            "location": None
                        },
                        {
                            "type": "ParagraphNode",
                            "paragraph_name": "PARAGRAPH",
                            "statements": [],
                            "location": None
                        }
                    ],
                    "location": None
                }
            ],
            "location": None
        }
    ],
    "location": None
}

print("Testing build_cfg with provided AST...")
print("=" * 80)

try:
    result = build_cfg_handler({"ast": ast_data})

    print(f"Success: {result.get('success')}")

    if result.get('success'):
        print(f"\n✅ CFG built successfully!")
        print(f"   Node count: {result.get('node_count')}")
        print(f"   Edge count: {result.get('edge_count')}")
        print(f"\nCFG structure:")
        print(json.dumps(result, indent=2))
    else:
        print(f"\n❌ Error: {result.get('error')}")

except Exception as e:
    print(f"\n❌ Exception occurred:")
    print(f"   Type: {type(e).__name__}")
    print(f"   Message: {str(e)}")
    import traceback
    print(f"\nFull traceback:")
    traceback.print_exc()

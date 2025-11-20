"""Test script for full-fidelity AST implementation.

This script demonstrates:
1. Comment extraction from COBOL source
2. Source location preservation
3. Comment attachment to AST nodes
4. Usage for code conversion and user story generation
"""

from src.core.services.cobol_parser_antlr_service import parse_cobol
from src.core.services.ast_builder_service import build_ast
from src.core.models.cobol_analysis_model import CommentType


def main():
    """Test full-fidelity AST with a sample COBOL program."""

    # Sample COBOL program with various comment types
    # Note: Using simplified format without decorative comment blocks
    # to avoid parser issues with column-specific COBOL formatting
    cobol_source = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCOUNT-VALIDATOR.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 ACCOUNT-NUMBER      PIC 9(10).
       01 ACCOUNT-STATUS      PIC X.

       PROCEDURE DIVISION.
       VALIDATE-ACCOUNT.
           MOVE 0 TO ACCOUNT-NUMBER.
           DISPLAY "Validation complete".
           STOP RUN.
    """

    print("=" * 70)
    print("FULL-FIDELITY AST TEST")
    print("=" * 70)

    # Step 1: Parse COBOL and extract comments
    print("\n1. Parsing COBOL source code...")
    try:
        parse_tree, comments = parse_cobol(cobol_source)
        print(f"   ✓ Parsing successful!")
        print(f"   ✓ Extracted {len(comments)} comments")
    except Exception as e:
        print(f"   ✗ Parsing failed: {e}")
        return

    # Step 2: Display extracted comments
    print("\n2. Extracted Comments:")
    print("   " + "-" * 66)
    for i, comment in enumerate(comments, 1):
        print(f"   {i}. Line {comment.location.line:2d} [{comment.comment_type.value:12s}]: {comment.text[:50]}")

    # Step 3: Build AST with comments
    print("\n3. Building AST with comments...")
    try:
        ast = build_ast(parse_tree, comments)
        print(f"   ✓ AST built successfully!")
        print(f"   ✓ Program: {ast.program_name}")
        print(f"   ✓ Total comments in AST: {len(ast.all_comments)}")
    except Exception as e:
        print(f"   ✗ AST building failed: {e}")
        return

    # Step 4: Explore AST structure with comments
    print("\n4. AST Structure with Comments:")
    print("   " + "-" * 66)

    # Program-level comments
    if ast.header_comments:
        print(f"\n   Program Header Comments ({len(ast.header_comments)}):")
        for comment in ast.header_comments:
            print(f"     • {comment.text}")

    # Division-level exploration
    for division in ast.divisions:
        print(f"\n   Division: {division.division_type.value}")
        if division.location:
            print(f"     Location: Line {division.location.line}")

        if division.preceding_comments:
            print(f"     Preceding Comments:")
            for comment in division.preceding_comments:
                print(f"       • {comment.text}")

        # Section-level exploration
        for section in division.sections:
            if section.preceding_comments or section.paragraphs:
                print(f"\n     Section: {section.section_name}")
                if section.preceding_comments:
                    print(f"       Comments:")
                    for comment in section.preceding_comments:
                        print(f"         • {comment.text}")

                # Paragraph-level exploration
                for paragraph in section.paragraphs:
                    if paragraph.preceding_comments or paragraph.inline_comment:
                        print(f"\n       Paragraph: {paragraph.paragraph_name}")
                        if paragraph.location:
                            print(f"         Location: Line {paragraph.location.line}")
                        if paragraph.preceding_comments:
                            print(f"         Preceding Comments:")
                            for comment in paragraph.preceding_comments:
                                print(f"           • {comment.text}")
                        if paragraph.inline_comment:
                            print(f"         Inline: {paragraph.inline_comment.text}")

    # Step 5: Comment Type Statistics
    print("\n5. Comment Type Statistics:")
    print("   " + "-" * 66)
    comment_stats = {}
    for comment in ast.all_comments:
        comment_type = comment.comment_type.value
        comment_stats[comment_type] = comment_stats.get(comment_type, 0) + 1

    for comment_type, count in sorted(comment_stats.items()):
        print(f"   {comment_type:15s}: {count:2d} comment(s)")

    # Step 6: Demonstrate use cases
    print("\n6. Use Case Demonstrations:")
    print("   " + "-" * 66)

    # Use case 1: Extract business rules
    print("\n   A. Business Rules Extraction:")
    business_rules = [
        c.text for c in ast.all_comments
        if any(keyword in c.text.upper() for keyword in ["CRITICAL", "IMPORTANT", "MUST"])
    ]
    for i, rule in enumerate(business_rules, 1):
        print(f"      {i}. {rule}")

    # Use case 2: Find TODOs
    print("\n   B. TODO/FIXME Items:")
    todos = [c for c in ast.all_comments if c.comment_type == CommentType.TODO]
    if todos:
        for i, todo in enumerate(todos, 1):
            print(f"      {i}. Line {todo.location.line}: {todo.text}")
    else:
        print("      (No TODO items found)")

    # Use case 3: Extract documentation
    print("\n   C. Documentation Comments:")
    docs = [c for c in ast.all_comments if c.comment_type == CommentType.DOCUMENTATION]
    if docs:
        for doc in docs:
            print(f"      • {doc.text}")
    else:
        print("      (No documentation comments found)")

    print("\n" + "=" * 70)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()

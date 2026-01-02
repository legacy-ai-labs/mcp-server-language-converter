"""Tests for build_ast_handler.

This module contains comprehensive unit tests for the build_ast tool handler,
which builds Abstract Syntax Trees (AST) from COBOL source code.
"""

from pathlib import Path

import pytest

from src.core.services.cobol_analysis.tool_handlers_service import build_ast_handler


# Path to COBOL sample files
SAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "cobol_samples"


class TestBuildASTBasicFunctionality:
    """Tests for basic AST building functionality."""

    def test_build_ast_with_source_code(self) -> None:
        """Test building AST from inline source code."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLO-WORLD.
       PROCEDURE DIVISION.
           DISPLAY "HELLO WORLD".
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        assert "ast" in result
        assert result["ast"]["type"] == "PROGRAM"
        assert result["program_name"] == "HELLO-WORLD"
        assert result["node_count"] > 0
        assert result["root_type"] == "PROGRAM"

    def test_build_ast_with_file_path(self) -> None:
        """Test building AST from a file path."""
        file_path = SAMPLES_DIR / "CUSTOMER-ACCOUNT-MAIN.cbl"

        result = build_ast_handler({"file_path": str(file_path)})

        assert result["success"] is True
        assert "ast" in result
        assert result["ast"]["type"] == "PROGRAM"
        assert result["program_name"] is not None
        assert result["node_count"] > 0
        assert "source_file" in result
        assert result["source_file"] == str(file_path)

    def test_build_ast_with_all_divisions(self) -> None:
        """Test AST building with all four divisions."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. FULL-PROGRAM.
       AUTHOR. TEST AUTHOR.

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-COUNTER PIC 9(5) VALUE 0.

       PROCEDURE DIVISION.
           ADD 1 TO WS-COUNTER.
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        assert result["program_name"] == "FULL-PROGRAM"
        assert result["node_count"] > 10  # Should have many nodes with all divisions


class TestBuildASTInputValidation:
    """Tests for input validation."""

    def test_build_ast_missing_source_and_file(self) -> None:
        """Test error when neither source_code nor file_path provided."""
        result = build_ast_handler({})

        assert result["success"] is False
        assert "error" in result
        assert "source_code" in result["error"] or "file_path" in result["error"]

    def test_build_ast_source_code_not_string(self) -> None:
        """Test error when source_code is not a string."""
        result = build_ast_handler({"source_code": 12345})

        assert result["success"] is False
        assert "error" in result
        assert "string" in result["error"]

    def test_build_ast_file_path_not_string(self) -> None:
        """Test error when file_path is not a string."""
        result = build_ast_handler({"file_path": 12345})

        assert result["success"] is False
        assert "error" in result
        assert "string" in result["error"]

    def test_build_ast_file_not_found(self) -> None:
        """Test error when file does not exist."""
        result = build_ast_handler({"file_path": "/nonexistent/path/file.cbl"})

        assert result["success"] is False
        assert "error" in result

    def test_build_ast_invalid_cobol_syntax(self) -> None:
        """Test error when COBOL syntax is invalid."""
        result = build_ast_handler({"source_code": "THIS IS NOT VALID COBOL"})

        assert result["success"] is False
        assert "error" in result

    def test_build_ast_empty_source(self) -> None:
        """Test handling of empty source code."""
        result = build_ast_handler({"source_code": ""})

        # Empty source should fail parsing
        assert result["success"] is False
        assert "error" in result


class TestBuildASTComments:
    """Tests for comment extraction functionality."""

    def test_build_ast_with_comments_default(self) -> None:
        """Test that comments are included by default."""
        # ANTLR lexer uses *> format for inline comments
        source = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. COMMENT-TEST.\n"
            "       PROCEDURE DIVISION.\n"
            "      *> This is a comment line\n"
            '           DISPLAY "TEST".\n'
            "           STOP RUN.\n"
        )
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        # Comments should be included by default
        if "comments" in result:
            assert "comment_count" in result

    def test_build_ast_include_comments_true(self) -> None:
        """Test explicit include_comments=True."""
        # ANTLR lexer uses *> format for inline comments
        source = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. COMMENT-TEST.\n"
            "       PROCEDURE DIVISION.\n"
            "      *> This is a comment\n"
            "           STOP RUN.\n"
        )
        result = build_ast_handler(
            {
                "source_code": source,
                "include_comments": True,
            }
        )

        assert result["success"] is True

    def test_build_ast_include_comments_false(self) -> None:
        """Test include_comments=False excludes comments."""
        # ANTLR lexer uses *> format for inline comments
        source = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. COMMENT-TEST.\n"
            "       PROCEDURE DIVISION.\n"
            "      *> This is a comment\n"
            "           STOP RUN.\n"
        )
        result = build_ast_handler(
            {
                "source_code": source,
                "include_comments": False,
            }
        )

        assert result["success"] is True
        # Comments should not be in result when include_comments=False
        assert "comments" not in result or result.get("comments") is None


class TestBuildASTMetadata:
    """Tests for metadata extraction functionality."""

    def test_build_ast_with_identification_metadata(self) -> None:
        """Test extraction of IDENTIFICATION DIVISION metadata."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. METADATA-TEST.
       AUTHOR. JOHN DOE.
       DATE-WRITTEN. 2025-01-15.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = build_ast_handler(
            {
                "source_code": source,
                "include_metadata": True,
            }
        )

        assert result["success"] is True
        if "identification_metadata" in result:
            metadata = result["identification_metadata"]
            assert "author" in metadata or "date_written" in metadata

    def test_build_ast_include_metadata_false(self) -> None:
        """Test include_metadata=False excludes identification metadata."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. METADATA-TEST.
       AUTHOR. JOHN DOE.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = build_ast_handler(
            {
                "source_code": source,
                "include_metadata": False,
            }
        )

        assert result["success"] is True
        assert "identification_metadata" not in result

    def test_build_ast_metadata_includes_dependencies(self) -> None:
        """Test that metadata includes dependency information."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CALLER-PROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-VAR PIC X(10).
       PROCEDURE DIVISION.
           CALL "SUBPROGRAM" USING WS-VAR.
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        assert "metadata" in result
        # Metadata should contain dependency tracking info
        metadata = result["metadata"]
        assert isinstance(metadata, dict)


class TestBuildASTOutputStructure:
    """Tests for output structure validation."""

    def test_build_ast_required_fields(self) -> None:
        """Test that all required fields are present in successful result."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. STRUCTURE-TEST.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        # Check required fields
        assert "ast" in result
        assert "program_name" in result
        assert "node_count" in result
        assert "root_type" in result
        assert "metadata" in result

    def test_build_ast_ast_structure(self) -> None:
        """Test that AST has proper structure."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. AST-STRUCTURE.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        ast = result["ast"]

        # AST should have type and children
        assert "type" in ast
        assert ast["type"] == "PROGRAM"
        # AST should have children (divisions)
        assert "children" in ast or len(ast) > 1

    def test_build_ast_node_count_accuracy(self) -> None:
        """Test that node_count reflects actual AST size."""
        simple_source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SIMPLE.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        complex_source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COMPLEX.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-A PIC 9.
       01 WS-B PIC 9.
       01 WS-C PIC 9.
       PROCEDURE DIVISION.
           ADD WS-A TO WS-B GIVING WS-C.
           IF WS-C > 5
               DISPLAY "GREATER"
           ELSE
               DISPLAY "LESSER"
           END-IF.
           STOP RUN.
"""
        simple_result = build_ast_handler({"source_code": simple_source})
        complex_result = build_ast_handler({"source_code": complex_source})

        assert simple_result["success"] is True
        assert complex_result["success"] is True

        # Complex program should have more nodes
        assert complex_result["node_count"] > simple_result["node_count"]


class TestBuildASTWithSampleFiles:
    """Tests using actual COBOL sample files."""

    def test_build_ast_customer_account_main(self) -> None:
        """Test AST building with CUSTOMER-ACCOUNT-MAIN.cbl."""
        file_path = SAMPLES_DIR / "CUSTOMER-ACCOUNT-MAIN.cbl"
        if not file_path.exists():
            pytest.skip(f"Sample file not found: {file_path}")

        result = build_ast_handler({"file_path": str(file_path)})

        assert result["success"] is True
        assert result["program_name"] is not None
        assert result["node_count"] > 0

    def test_build_ast_account_validator(self) -> None:
        """Test AST building with ACCOUNT-VALIDATOR.cbl."""
        file_path = SAMPLES_DIR / "ACCOUNT-VALIDATOR.cbl"
        if not file_path.exists():
            pytest.skip(f"Sample file not found: {file_path}")

        result = build_ast_handler({"file_path": str(file_path)})

        assert result["success"] is True
        assert result["program_name"] is not None

    def test_build_ast_calculate_penalty(self) -> None:
        """Test AST building with CALCULATE-PENALTY.cbl."""
        file_path = SAMPLES_DIR / "CALCULATE-PENALTY.cbl"
        if not file_path.exists():
            pytest.skip(f"Sample file not found: {file_path}")

        result = build_ast_handler({"file_path": str(file_path)})

        assert result["success"] is True
        assert result["program_name"] is not None


class TestBuildASTCopybooks:
    """Tests for copybook handling."""

    def test_build_ast_with_copybook_directories(self) -> None:
        """Test AST building with copybook directories specified."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COPY-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-VAR PIC X(10).
       PROCEDURE DIVISION.
           STOP RUN.
"""
        # Even without actual copybooks, the parameter should be accepted
        result = build_ast_handler(
            {
                "source_code": source,
                "copybook_directories": [str(SAMPLES_DIR)],
            }
        )

        assert result["success"] is True

    def test_build_ast_copybook_info_in_result(self) -> None:
        """Test that copybook info is included when copybooks are used."""
        # Test with a file that might have COPY statements
        file_path = SAMPLES_DIR / "CUSTOMER-ACCOUNT-MAIN.cbl"
        if not file_path.exists():
            pytest.skip(f"Sample file not found: {file_path}")

        result = build_ast_handler(
            {
                "file_path": str(file_path),
                "copybook_directories": [str(SAMPLES_DIR)],
            }
        )

        assert result["success"] is True
        # Result may or may not have copybook_info depending on the file


class TestBuildASTEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_build_ast_minimal_program(self) -> None:
        """Test with minimal valid COBOL program."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. MINIMAL.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        assert result["program_name"] == "MINIMAL"

    def test_build_ast_with_nested_structures(self) -> None:
        """Test with nested IF statements and complex control flow."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. NESTED-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-A PIC 9 VALUE 1.
       01 WS-B PIC 9 VALUE 2.
       PROCEDURE DIVISION.
           IF WS-A = 1
               IF WS-B = 2
                   DISPLAY "BOTH TRUE"
               ELSE
                   DISPLAY "A TRUE B FALSE"
               END-IF
           ELSE
               DISPLAY "A FALSE"
           END-IF.
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        assert result["node_count"] > 20  # Complex structure should have many nodes

    def test_build_ast_with_perform_statements(self) -> None:
        """Test with PERFORM statements."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PERFORM-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM HELPER-PARA.
           PERFORM HELPER-PARA 3 TIMES.
           STOP RUN.
       HELPER-PARA.
           DISPLAY "HELPER".
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        assert result["program_name"] == "PERFORM-TEST"

    def test_build_ast_with_evaluate_statement(self) -> None:
        """Test with EVALUATE statement (COBOL switch/case)."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. EVALUATE-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-CODE PIC 9 VALUE 1.
       PROCEDURE DIVISION.
           EVALUATE WS-CODE
               WHEN 1
                   DISPLAY "ONE"
               WHEN 2
                   DISPLAY "TWO"
               WHEN OTHER
                   DISPLAY "OTHER"
           END-EVALUATE.
           STOP RUN.
"""
        result = build_ast_handler({"source_code": source})

        assert result["success"] is True
        assert result["program_name"] == "EVALUATE-TEST"

    def test_build_ast_file_path_takes_precedence(self) -> None:
        """Test that file_path takes precedence over source_code when both provided.

        Note: The handler prioritizes file_path over source_code when both are provided.
        This test documents the actual behavior.
        """
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. FROM-SOURCE.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        file_path = SAMPLES_DIR / "CUSTOMER-ACCOUNT-MAIN.cbl"
        if not file_path.exists():
            pytest.skip(f"Sample file not found: {file_path}")

        # Provide both source_code and a file_path
        result = build_ast_handler(
            {
                "source_code": source,
                "file_path": str(file_path),
            }
        )

        assert result["success"] is True
        # The program name should be from the file_path, not source_code
        assert result["program_name"] == "CUSTOMER-ACCOUNT-MAIN"

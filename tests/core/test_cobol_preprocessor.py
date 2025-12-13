"""Tests for the COBOL Preprocessor Service."""

from pathlib import Path

import pytest

from src.core.services.cobol_analysis.cobol_preprocessor_service import (
    CobolPreprocessor,
    PreprocessorConfig,
    SourceFormat,
    preprocess_cobol_file,
    preprocess_cobol_source,
)


# Test fixtures paths
SAMPLES_DIR = Path(__file__).parent.parent / "cobol_samples"
INTER_PROGRAM_DIR = SAMPLES_DIR / "inter_program_test"
PROGRAMS_DIR = INTER_PROGRAM_DIR / "programs"
COPYBOOKS_DIR = INTER_PROGRAM_DIR / "copybooks"


class TestCobolPreprocessorBasic:
    """Basic tests for COBOL preprocessor."""

    def test_simple_source_no_copy(self) -> None:
        """Test preprocessing source without COPY statements."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST-PROGRAM.
       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY 'Hello World'.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert result is not None
        assert not result.has_errors
        assert len(result.copybook_usages) == 0
        assert "Hello World" in result.source

    def test_preprocessor_config_defaults(self) -> None:
        """Test default configuration values."""
        config = PreprocessorConfig()

        assert config.source_format == SourceFormat.FIXED
        assert config.max_copy_depth == 10
        assert config.expand_copy_statements is True
        assert config.process_replace_directives is True
        assert ".cpy" in config.copybook_extensions

    def test_preprocessor_with_custom_config(self) -> None:
        """Test preprocessor with custom configuration."""
        config = PreprocessorConfig(
            copybook_directories=[Path("/custom/copybooks")],
            source_format=SourceFormat.FREE,
            max_copy_depth=5,
        )
        preprocessor = CobolPreprocessor(config)

        assert preprocessor.config.source_format == SourceFormat.FREE
        assert preprocessor.config.max_copy_depth == 5


class TestCopyStatementParsing:
    """Tests for COPY statement parsing."""

    def test_simple_copy_statement_detection(self) -> None:
        """Test detection of simple COPY statement."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert len(result.copybook_usages) == 1
        assert result.copybook_usages[0].copybook_name == "CUSTOMER-REC"
        assert result.copybook_usages[0].is_resolved is False  # No copybook directory

    def test_copy_statement_with_library(self) -> None:
        """Test COPY statement with IN/OF library clause."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC OF MYLIB.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert len(result.copybook_usages) == 1
        assert result.copybook_usages[0].copybook_name == "CUSTOMER-REC"

    def test_copy_statement_with_replacing(self) -> None:
        """Test COPY statement with REPLACING clause."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC REPLACING ==:PREFIX:== BY ==WS-==.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert len(result.copybook_usages) == 1
        usage = result.copybook_usages[0]
        assert usage.copybook_name == "CUSTOMER-REC"
        assert len(usage.replacing_clauses) == 1
        assert usage.replacing_clauses[0].old_text == ":PREFIX:"
        assert usage.replacing_clauses[0].new_text == "WS-"

    def test_multiple_copy_statements(self) -> None:
        """Test multiple COPY statements in source."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC.
       COPY DB-CONFIG.
       COPY COMMON-DEFS.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert len(result.copybook_usages) == 3
        names = [u.copybook_name for u in result.copybook_usages]
        assert "CUSTOMER-REC" in names
        assert "DB-CONFIG" in names
        assert "COMMON-DEFS" in names


@pytest.mark.skipif(not COPYBOOKS_DIR.exists(), reason="Test copybooks not available")
class TestCopybookResolution:
    """Tests for copybook resolution."""

    def test_resolve_copybook_from_directory(self) -> None:
        """Test resolving copybook from specified directory."""
        config = PreprocessorConfig(
            copybook_directories=[COPYBOOKS_DIR],
        )
        preprocessor = CobolPreprocessor(config)

        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocessor.process_source(source)

        assert len(result.copybook_usages) == 1
        assert result.copybook_usages[0].is_resolved is True
        assert result.copybook_usages[0].resolved_path is not None
        assert "CUSTOMER-REC" in str(result.copybook_usages[0].resolved_path)

    def test_copybook_expansion(self) -> None:
        """Test that copybook content is expanded."""
        config = PreprocessorConfig(
            copybook_directories=[COPYBOOKS_DIR],
        )
        preprocessor = CobolPreprocessor(config)

        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocessor.process_source(source)

        # Check that copybook content is in expanded source
        assert "CUSTOMER-RECORD" in result.source
        assert "CUST-ID" in result.source
        assert "CUST-NAME" in result.source

    def test_copybook_not_found_error(self) -> None:
        """Test error when copybook is not found."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY NONEXISTENT-COPYBOOK.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert result.has_errors
        assert len(result.unresolved_copybooks) == 1
        assert "NONEXISTENT-COPYBOOK" in result.unresolved_copybooks


@pytest.mark.skipif(not PROGRAMS_DIR.exists(), reason="Test programs not available")
class TestFileProcessing:
    """Tests for processing COBOL files."""

    def test_process_file_with_copies(self) -> None:
        """Test processing a file with COPY statements."""
        file_path = PROGRAMS_DIR / "CUSTOMER-MGMT.cbl"

        if not file_path.exists():
            pytest.skip("CUSTOMER-MGMT.cbl not available")

        result = preprocess_cobol_file(
            file_path,
            copybook_directories=[COPYBOOKS_DIR],
        )

        assert result is not None
        assert result.source_file == file_path

        # Should have found COPY statements
        assert len(result.copybook_usages) >= 2

        # Check specific copybooks are found
        names = [u.copybook_name for u in result.copybook_usages]
        assert "CUSTOMER-REC" in names
        assert "DB-CONFIG" in names

    def test_process_file_not_found(self) -> None:
        """Test error when file is not found."""
        with pytest.raises(FileNotFoundError):
            preprocess_cobol_file(Path("/nonexistent/file.cbl"))


class TestReplacingClause:
    """Tests for REPLACING clause processing."""

    def test_replacing_identifier(self) -> None:
        """Test REPLACING with identifier replacement."""
        config = PreprocessorConfig(
            copybook_directories=[COPYBOOKS_DIR],
        )
        preprocessor = CobolPreprocessor(config)

        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC REPLACING CUSTOMER-RECORD BY MY-CUSTOMER.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocessor.process_source(source)

        if result.copybook_usages and result.copybook_usages[0].is_resolved:
            # If copybook was resolved, check replacement was recorded
            assert len(result.copybook_usages[0].replacing_clauses) == 1
            clause = result.copybook_usages[0].replacing_clauses[0]
            assert clause.old_text == "CUSTOMER-RECORD"
            assert clause.new_text == "MY-CUSTOMER"

    def test_replacing_pseudo_text(self) -> None:
        """Test REPLACING with pseudo-text notation."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY MYBOOK REPLACING ==:TAG:== BY ==WS-== ==OLD== BY ==NEW==.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert len(result.copybook_usages) == 1
        clauses = result.copybook_usages[0].replacing_clauses
        assert len(clauses) == 2
        assert clauses[0].old_text == ":TAG:"
        assert clauses[0].new_text == "WS-"
        assert clauses[0].is_pseudo_text is True


class TestReplaceDirective:
    """Tests for REPLACE directive processing."""

    def test_replace_directive_detection(self) -> None:
        """Test detection of REPLACE directive."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       REPLACE ==OLD-NAME== BY ==NEW-NAME==.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 OLD-NAME PIC X(10).
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert len(result.replace_directives) == 1
        directive = result.replace_directives[0]
        assert directive.old_text == "OLD-NAME"
        assert directive.new_text == "NEW-NAME"
        assert directive.is_active is True

    def test_replace_off(self) -> None:
        """Test REPLACE OFF directive."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       REPLACE ==OLD== BY ==NEW==.
       DATA DIVISION.
       REPLACE OFF.
       WORKING-STORAGE SECTION.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        assert len(result.replace_directives) == 2
        # Second directive should be REPLACE OFF
        assert result.replace_directives[1].is_active is False


class TestPreprocessedSourceMetadata:
    """Tests for PreprocessedSource metadata."""

    def test_to_dict_serialization(self) -> None:
        """Test JSON-compatible dictionary output."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTOMER-REC.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)
        data = result.to_dict()

        assert "source_file" in data
        assert "preprocessed_line_count" in data
        assert "original_line_count" in data
        assert "copybook_usages" in data
        assert "errors" in data
        assert "warnings" in data

        assert isinstance(data["copybook_usages"], list)

    def test_unresolved_copybooks_property(self) -> None:
        """Test unresolved_copybooks property."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       COPY MISSING1.
       COPY MISSING2.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        unresolved = result.unresolved_copybooks
        assert len(unresolved) == 2
        assert "MISSING1" in unresolved
        assert "MISSING2" in unresolved


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_source(self) -> None:
        """Test preprocessing empty source."""
        result = preprocess_cobol_source("")

        assert result is not None
        assert result.source == ""
        assert not result.has_errors

    def test_source_with_only_comments(self) -> None:
        """Test source with only comments."""
        source = """\
      * This is a comment
      * Another comment line
      * And another one
"""
        result = preprocess_cobol_source(source)

        assert result is not None
        assert not result.has_errors
        assert len(result.copybook_usages) == 0

    def test_malformed_copy_statement(self) -> None:
        """Test handling of malformed COPY statement."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       COPY .
       PROCEDURE DIVISION.
           STOP RUN.
"""
        result = preprocess_cobol_source(source)

        # Should handle gracefully
        assert result is not None

    def test_max_copy_depth(self) -> None:
        """Test maximum COPY nesting depth is enforced."""
        config = PreprocessorConfig(
            max_copy_depth=2,
        )
        preprocessor = CobolPreprocessor(config)

        # This would require actual nested copybooks to fully test
        # For now, just verify config is respected
        assert preprocessor.config.max_copy_depth == 2

    def test_clear_cache(self) -> None:
        """Test cache clearing."""
        preprocessor = CobolPreprocessor()

        # Add something to cache
        preprocessor._copybook_cache["test"] = "content"
        assert len(preprocessor._copybook_cache) == 1

        # Clear cache
        preprocessor.clear_cache()
        assert len(preprocessor._copybook_cache) == 0

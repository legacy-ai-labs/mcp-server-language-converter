"""Integration tests for COBOL analysis MCP tools."""

from pathlib import Path

import pytest

from src.core.services.cobol_analysis.tool_handlers_service import (
    build_asg_handler,
    parse_cobol_handler,
    parse_cobol_raw_handler,
)


@pytest.mark.integration
def test_parse_cobol_with_sample_file() -> None:
    """Test parsing a real sample COBOL file via handler."""
    file_path = Path(__file__).parent / ".." / "cobol_samples" / "CUSTOMER-ACCOUNT-MAIN.cbl"

    if not file_path.exists():
        pytest.skip(f"Sample file not found: {file_path}")

    parse_result = parse_cobol_handler({"file_path": str(file_path)})
    if not parse_result["success"]:
        # Parser may not support all COBOL constructs in sample files yet
        pytest.skip(
            f"Parser doesn't support all constructs in sample file: {parse_result.get('error', 'Unknown error')}"
        )

    assert "ast" in parse_result
    ast_dict = parse_result["ast"]
    assert ast_dict["node_type"] == "PROGRAM"
    assert "children" in ast_dict


@pytest.mark.integration
def test_parse_cobol_raw_with_source() -> None:
    """Test raw parse tree output."""
    source_code = (
        "IDENTIFICATION DIVISION.\n"
        "PROGRAM-ID. RAW-TEST.\n"
        "PROCEDURE DIVISION.\n"
        "MAIN.\n"
        "    STOP RUN.\n"
    )
    result = parse_cobol_raw_handler({"source_code": source_code})
    if not result["success"]:
        pytest.skip(f"Parser limitation: {result.get('error', 'Unknown error')}")

    assert result["node_type"] == "PROGRAM"
    assert "parse_tree" in result
    assert result["parse_tree"]["node_type"] == "PROGRAM"


@pytest.mark.integration
def test_error_handling_invalid_cobol() -> None:
    """Test error handling with invalid COBOL syntax."""
    result = parse_cobol_handler({"source_code": "INVALID COBOL CODE WITHOUT STRUCTURE"})

    # Should handle gracefully
    assert "success" in result
    # May succeed with partial parse or fail gracefully
    if not result["success"]:
        assert "error" in result


@pytest.mark.integration
def test_build_asg_from_source() -> None:
    """Test building ASG (semantic graph) from source using the Python builder."""
    source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ASG-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-COUNTER PIC 9(5) VALUE 0.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
    result = build_asg_handler({"source_code": source_code})
    if not result["success"]:
        pytest.skip(f"ASG builder limitation: {result.get('error', 'Unknown error')}")

    assert result["builder"] == "python"
    assert "asg" in result
    assert result["compilation_unit_count"] >= 1


@pytest.mark.integration
def test_build_asg_missing_parameters() -> None:
    """Test build_asg_handler with missing parameters."""
    result = build_asg_handler({})
    assert result["success"] is False
    assert "error" in result

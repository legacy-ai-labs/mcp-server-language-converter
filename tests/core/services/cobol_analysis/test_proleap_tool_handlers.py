"""Tests for ProLeap tool handlers."""

from unittest.mock import AsyncMock, patch

from src.core.services.cobol_analysis.tool_handlers_service import (
    proleap_analyze_cobol_handler,
    proleap_interpret_cobol_handler,
    proleap_transform_cobol_handler,
)


# Patch targets: the handlers do lazy imports from proleap_client_service,
# so we patch at the source module.
_CLIENT = "src.core.services.cobol_analysis.proleap_client_service"

SAMPLE_COBOL = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLO.
       PROCEDURE DIVISION.
       DISPLAY "HELLO".
       STOP RUN.
"""


class TestProLeapHandlers:
    async def test_analyze_missing_source_code(self):
        result = await proleap_analyze_cobol_handler({})
        assert result["success"] is False
        assert "source_code is required" in result["error"]

    async def test_transform_missing_source_code(self):
        result = await proleap_transform_cobol_handler({})
        assert result["success"] is False
        assert "source_code is required" in result["error"]

    async def test_interpret_missing_source_code(self):
        result = await proleap_interpret_cobol_handler({})
        assert result["success"] is False
        assert "source_code is required" in result["error"]

    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=False)
    async def test_analyze_service_unavailable(self, _mock):
        result = await proleap_analyze_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is False
        assert "not available" in result["error"]

    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=False)
    async def test_transform_service_unavailable(self, _mock):
        result = await proleap_transform_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is False
        assert "not available" in result["error"]

    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=False)
    async def test_interpret_service_unavailable(self, _mock):
        result = await proleap_interpret_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is False
        assert "not available" in result["error"]

    @patch(
        f"{_CLIENT}.proleap_analyze",
        new_callable=AsyncMock,
        return_value={"issues": [{"description": "test issue", "severity": 1}]},
    )
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_analyze_delegates_to_client(self, _avail, mock_analyze):
        result = await proleap_analyze_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is True
        assert result["issue_count"] == 1
        assert result["issues"][0]["description"] == "test issue"
        assert result["issues"][0]["severity"] == "WARNING"
        assert result["issues"][0]["category"] == "other"
        mock_analyze.assert_called_once_with(SAMPLE_COBOL, format="FIXED")

    @patch(
        f"{_CLIENT}.proleap_transform",
        new_callable=AsyncMock,
        return_value={"success": True, "java_source": "class Hello {}"},
    )
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_transform_delegates_to_client(self, _avail, mock_transform):
        result = await proleap_transform_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is True
        mock_transform.assert_called_once_with(SAMPLE_COBOL, format="FIXED")

    @patch(
        f"{_CLIENT}.proleap_execute",
        new_callable=AsyncMock,
        return_value={"success": True, "output": "HELLO"},
    )
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_interpret_delegates_to_client(self, _avail, mock_execute):
        result = await proleap_interpret_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is True
        mock_execute.assert_called_once_with(SAMPLE_COBOL, format="FIXED")

    @patch(f"{_CLIENT}.proleap_analyze", new_callable=AsyncMock, return_value={"issues": []})
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_analyze_passes_format(self, _avail, mock_analyze):
        result = await proleap_analyze_cobol_handler(
            {"source_code": SAMPLE_COBOL, "format": "FREE"}
        )
        assert result["success"] is True
        assert result["issue_count"] == 0
        mock_analyze.assert_called_once_with(SAMPLE_COBOL, format="FREE")

    @patch(
        f"{_CLIENT}.proleap_analyze",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "ProLeap error: something failed"},
    )
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_analyze_error_passes_through(self, _avail, _mock_analyze):
        result = await proleap_analyze_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is False
        assert "something failed" in result["error"]

    @patch(
        f"{_CLIENT}.proleap_analyze",
        new_callable=AsyncMock,
        return_value={
            "success": False,
            "error": "ProLeap error: class io.proleap.cobol.asg.metamodel.call.impl.UndefinedCallImpl cannot be cast to class io.proleap.cobol.asg.metamodel.call.TableCall",
        },
    )
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_analyze_humanizes_abs_linkage_error(self, _avail, _mock_analyze):
        result = await proleap_analyze_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is False
        assert "intrinsic function" in result["error"]
        assert "ABS" in result["error"]
        assert "LINKAGE" in result["error"]
        assert "UndefinedCallImpl" not in result["error"]

    @patch(
        f"{_CLIENT}.proleap_analyze",
        new_callable=AsyncMock,
        return_value={
            "issues": [
                {"description": "Obsolete keyword at example.", "severity": 1},
                {"description": "Obsolete keyword at example.", "severity": 1},
                {"description": "Some other issue", "severity": 0},
            ],
        },
    )
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_analyze_enriches_obsolete_keyword_issues(self, _avail, _mock):
        cobol_with_obsolete = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLO.
       AUTHOR. Test Suite.
       DATE-WRITTEN. 2024.
       PROCEDURE DIVISION.
       DISPLAY "HELLO".
       STOP RUN.
"""
        result = await proleap_analyze_cobol_handler({"source_code": cobol_with_obsolete})
        assert result["success"] is True
        assert result["issue_count"] == 3
        assert "AUTHOR" in result["issues"][0]["description"]
        assert result["issues"][0]["category"] == "standard"
        assert "DATE-WRITTEN" in result["issues"][1]["description"]
        assert result["issues"][1]["category"] == "standard"
        assert result["issues"][2]["description"] == "Some other issue"

    @patch(
        f"{_CLIENT}.proleap_analyze",
        new_callable=AsyncMock,
        return_value={
            "issues": [
                {"description": "GOBACK should be used instead of STOP RUN", "severity": 1},
                {"description": "Paragraphs should not be used at example.MAIN", "severity": 1},
                {
                    "description": "For portability reasons computational fields (except COMP-5) should not be used at example.WS-X",
                    "severity": 1,
                },
                {
                    "description": "Numbers that come out of nowhere (magic numbers) might be hard to understand at debugging time.",
                    "severity": 0,
                },
                {"description": "Paragraph example.UNUSED is uncalled", "severity": 0},
            ],
        },
    )
    @patch(f"{_CLIENT}.is_proleap_available", new_callable=AsyncMock, return_value=True)
    async def test_analyze_classifies_issues_by_category(self, _avail, _mock):
        result = await proleap_analyze_cobol_handler({"source_code": SAMPLE_COBOL})
        assert result["success"] is True
        assert result["issue_count"] == 5

        # Check categories
        assert result["issues"][0]["category"] == "best_practice"
        assert "note" in result["issues"][0]
        assert result["issues"][1]["category"] == "style_opinion"
        assert "note" in result["issues"][1]
        assert result["issues"][2]["category"] == "style_opinion"
        assert result["issues"][3]["category"] == "code_quality"
        assert result["issues"][4]["category"] == "code_quality"

        # Check category summary
        assert result["category_summary"]["best_practice"] == 1
        assert result["category_summary"]["style_opinion"] == 2
        assert result["category_summary"]["code_quality"] == 2

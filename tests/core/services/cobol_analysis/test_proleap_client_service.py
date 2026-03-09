"""Tests for the ProLeap async HTTP client service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.services.cobol_analysis.proleap_client_service import (
    _record_failure,
    _record_success,
    check_proleap_health,
    is_proleap_available,
    proleap_analyze,
    proleap_build_asg,
    proleap_execute,
    proleap_parse,
    proleap_transform,
    reset_circuit_breaker,
)


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Reset circuit breaker state before each test."""
    reset_circuit_breaker()
    yield
    reset_circuit_breaker()


# ---------------------------------------------------------------------------
# Circuit breaker tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    async def test_starts_closed(self):
        assert await is_proleap_available() is False  # disabled by default

    @patch("src.core.services.cobol_analysis.proleap_client_service.get_settings")
    async def test_available_when_enabled(self, mock_settings):
        mock_settings.return_value = MagicMock(
            proleap_service_enabled=True,
            proleap_service_url="http://localhost:4567",
            proleap_service_timeout=5,
        )
        assert await is_proleap_available() is True

    @patch("src.core.services.cobol_analysis.proleap_client_service.get_settings")
    async def test_opens_after_threshold(self, mock_settings):
        mock_settings.return_value = MagicMock(
            proleap_service_enabled=True,
            proleap_service_url="http://localhost:4567",
            proleap_service_timeout=5,
        )
        for _ in range(5):
            _record_failure()
        assert await is_proleap_available() is False

    @patch("src.core.services.cobol_analysis.proleap_client_service.get_settings")
    async def test_success_resets_breaker(self, mock_settings):
        mock_settings.return_value = MagicMock(
            proleap_service_enabled=True,
            proleap_service_url="http://localhost:4567",
            proleap_service_timeout=5,
        )
        for _ in range(4):
            _record_failure()
        _record_success()
        assert await is_proleap_available() is True


# ---------------------------------------------------------------------------
# HTTP client tests (mocked)
# ---------------------------------------------------------------------------


class TestProLeapClient:
    @patch("src.core.services.cobol_analysis.proleap_client_service._get_client")
    async def test_parse_success(self, mock_get_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "parse_tree": {}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        result = await proleap_parse("IDENTIFICATION DIVISION.", format="FIXED")
        assert result["success"] is True
        mock_client.post.assert_called_once()

    @patch("src.core.services.cobol_analysis.proleap_client_service._get_client")
    async def test_build_asg_success(self, mock_get_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "asg": {}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        result = await proleap_build_asg("IDENTIFICATION DIVISION.")
        assert result["success"] is True

    @patch("src.core.services.cobol_analysis.proleap_client_service._get_client")
    async def test_analyze_success(self, mock_get_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "issues": []}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        result = await proleap_analyze("IDENTIFICATION DIVISION.")
        assert result["success"] is True

    @patch("src.core.services.cobol_analysis.proleap_client_service._get_client")
    async def test_transform_success(self, mock_get_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "java_source": "class A {}"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        result = await proleap_transform("IDENTIFICATION DIVISION.")
        assert result["success"] is True

    @patch("src.core.services.cobol_analysis.proleap_client_service._get_client")
    async def test_execute_success(self, mock_get_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "output": "HELLO"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        result = await proleap_execute("IDENTIFICATION DIVISION.")
        assert result["success"] is True

    @patch("src.core.services.cobol_analysis.proleap_client_service._get_client")
    async def test_connection_error_returns_error_dict(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_get_client.return_value = mock_client

        result = await proleap_parse("IDENTIFICATION DIVISION.")
        assert result["success"] is False
        assert "error" in result

    async def test_circuit_open_returns_error(self):
        for _ in range(5):
            _record_failure()
        result = await proleap_parse("IDENTIFICATION DIVISION.")
        assert result["success"] is False
        assert "circuit breaker" in result["error"].lower()

    @patch("src.core.services.cobol_analysis.proleap_client_service._get_client")
    async def test_health_check(self, mock_get_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "ok",
            "version": "1.0.0",
            "capabilities": ["parse", "asg"],
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_get_client.return_value = mock_client

        health = await check_proleap_health()
        assert health.status == "ok"
        assert health.version == "1.0.0"

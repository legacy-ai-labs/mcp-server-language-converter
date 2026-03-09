"""Async HTTP client for the ProLeap Java sidecar service.

Provides functions to call ProLeap endpoints with:
- Connection pooling via a module-level httpx.AsyncClient
- Simple circuit breaker (closed -> open -> half-open -> closed)
- Typed return values using Pydantic schemas
"""
# ruff: noqa: PLW0603  # Module-level mutable state is inherent to circuit breaker pattern

import logging
import time
from typing import Any

import httpx

from src.core.config import get_settings
from src.core.schemas.proleap_schemas import ProLeapHealthStatus


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

_FAILURE_THRESHOLD = 5
_RESET_TIMEOUT_SECONDS = 30.0

_circuit_state: str = "closed"  # closed | open | half_open
_failure_count: int = 0
_last_failure_time: float = 0.0


def _record_success() -> None:
    global _circuit_state, _failure_count
    _failure_count = 0
    _circuit_state = "closed"


def _record_failure() -> None:
    global _circuit_state, _failure_count, _last_failure_time
    _failure_count += 1
    _last_failure_time = time.monotonic()
    if _failure_count >= _FAILURE_THRESHOLD:
        _circuit_state = "open"
        logger.warning("ProLeap circuit breaker OPEN after %d failures", _failure_count)


def _is_circuit_open() -> bool:
    global _circuit_state
    if _circuit_state == "closed":
        return False
    if _circuit_state == "open":
        elapsed = time.monotonic() - _last_failure_time
        if elapsed >= _RESET_TIMEOUT_SECONDS:
            _circuit_state = "half_open"
            logger.info("ProLeap circuit breaker HALF-OPEN, allowing probe request")
            return False
        return True
    # half_open — allow one request through
    return False


def reset_circuit_breaker() -> None:
    """Reset circuit breaker to closed state (useful for testing)."""
    global _circuit_state, _failure_count, _last_failure_time
    _circuit_state = "closed"
    _failure_count = 0
    _last_failure_time = 0.0


# ---------------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------------

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        settings = get_settings()
        _client = httpx.AsyncClient(
            base_url=settings.proleap_service_url,
            timeout=httpx.Timeout(settings.proleap_service_timeout),
        )
    return _client


async def close_client() -> None:
    """Close the HTTP client (call on shutdown)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def is_proleap_available() -> bool:
    """Check if ProLeap service is enabled and circuit breaker is closed."""
    settings = get_settings()
    if not settings.proleap_service_enabled:
        return False
    return not _is_circuit_open()


async def check_proleap_health() -> ProLeapHealthStatus:
    """GET /v1/cobol/health — returns service health status."""
    client = _get_client()
    try:
        resp = await client.get("/v1/cobol/health")
        resp.raise_for_status()
        data = resp.json()
        _record_success()
        return ProLeapHealthStatus(**data)
    except Exception as exc:
        _record_failure()
        raise ConnectionError(f"ProLeap health check failed: {exc}") from exc


async def proleap_parse(code: str, format: str = "FIXED") -> dict[str, Any]:
    """POST /v1/cobol/parse/text — parse COBOL to AST."""
    return await _post("/v1/cobol/parse/text", code=code, format=format)


async def proleap_build_asg(code: str, format: str = "FIXED") -> dict[str, Any]:
    """POST /v1/cobol/asg/text — build full ASG."""
    return await _post("/v1/cobol/asg/text", code=code, format=format)


async def proleap_analyze(code: str, format: str = "FIXED") -> dict[str, Any]:
    """POST /v1/cobol/analyze/text — static analysis (AGPL route)."""
    return await _post("/v1/cobol/analyze/text", code=code, format=format)


async def proleap_transform(code: str, format: str = "FIXED") -> dict[str, Any]:
    """POST /v1/cobol/transform/text — COBOL-to-Java transformation (AGPL route)."""
    return await _post("/v1/cobol/transform/text", code=code, format=format)


async def proleap_execute(code: str, format: str = "FIXED") -> dict[str, Any]:
    """POST /v1/cobol/execute/text — interpret COBOL in JVM (AGPL route)."""
    return await _post("/v1/cobol/execute/text", code=code, format=format)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


async def _post(path: str, *, code: str, format: str = "FIXED") -> dict[str, Any]:
    """Send a POST request to the ProLeap service with circuit breaker."""
    if _is_circuit_open():
        return {
            "success": False,
            "error": "ProLeap service circuit breaker is open. Retrying later.",
        }

    client = _get_client()
    try:
        resp = await client.post(path, json={"code": code, "format": format})
        resp.raise_for_status()
        _record_success()

        # Some ProLeap endpoints (e.g. /transform) return plain text, not JSON
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            data: dict[str, Any] = resp.json()
            return data
        return {"success": True, "result": resp.text}
    except httpx.HTTPStatusError as exc:
        _record_failure()
        try:
            body = exc.response.json()
            error_msg = body.get("error", str(exc))
        except Exception:
            # ProLeap AGPL servlets may return plain text errors
            raw = exc.response.text.strip()
            error_msg = raw if raw else str(exc)
        return {"success": False, "error": f"ProLeap error: {error_msg}"}
    except Exception as exc:
        _record_failure()
        return {"success": False, "error": f"ProLeap service error: {exc}"}

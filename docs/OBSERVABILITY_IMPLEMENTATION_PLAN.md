# Observability & Metrics Implementation Plan (REVISED for Prometheus)

## Overview

This document outlines the detailed implementation plan for adding comprehensive observability and metrics to the MCP Server Language Converter. The implementation uses **Prometheus for operational metrics** and **PostgreSQL for detailed audit trails**.

**Last Updated:** Phase 2 completed with Prometheus integration

## Goals

- ✅ Track execution count per tool
- ✅ Calculate success/failure rates
- ✅ Measure average execution time and percentile latencies (p50, p75, p90, p95, p99)
- ✅ Identify error patterns and anomalies
- ✅ Enable E2E tracing with correlation_id/session_id
- ✅ Export system metrics (counters, timers, per-tool breakdown)
- ✅ Provide real-time and historical metrics

## Architecture

### Hybrid Approach: Prometheus + Database

**Best of both worlds:** Industry-standard monitoring + detailed debugging

| Component | Purpose | Storage | Query Method |
|-----------|---------|---------|--------------|
| **Prometheus** | Operational metrics, alerting, dashboards | Time-series (15-365 days) | PromQL |
| **PostgreSQL** | Detailed audit trail, debugging | Relational (30+ days) | SQL |

#### 1. **Prometheus** (Real-time Operational Metrics)
- Counter: `mcp_tool_calls_total` - Total calls with labels (tool, status, domain, transport)
- Counter: `mcp_tool_errors_total` - Errors by type
- Histogram: `mcp_tool_duration_seconds` - Latency distribution (auto-calculates percentiles)
- Gauge: `mcp_tool_in_progress` - Current in-flight requests
- Native Grafana integration
- Built-in alerting via Alertmanager
- Industry-standard, battle-tested

#### 2. **Database** (Detailed Audit Trail)
- Individual execution records with full context
- Structured queries (SQL) for parameter analysis
- E2E tracing with correlation IDs
- Long-term retention for compliance
- Debug specific failures with input/output data

**Why both?**
- Prometheus: "Is system healthy? Alert if error rate > 5%"
- Database: "Why did this specific call fail with these parameters?"

## Implementation Status

### ✅ Phase 1: Database Foundation (COMPLETED)
**Status:** Implemented and migrated
**Branch:** `feature/observability-metrics`
**Commit:** `6077fa2`

- ✅ Alembic migration system initialized
- ✅ `tool_executions` table with 9 optimized indexes
- ✅ `ToolExecution` SQLAlchemy model
- ✅ `ToolExecutionRepository` with CRUD and metrics queries
- ✅ Migration applied to database

**Files Created:**
- `migrations/versions/d483646e26ae_add_tool_executions_table.py`
- `src/core/models/tool_execution_model.py`
- `src/core/repositories/tool_execution_repository.py`
- `alembic.ini`
- `migrations/env.py`

---

### ✅ Phase 2: Core Instrumentation (COMPLETED)
**Status:** Implemented, not yet committed
**Branch:** `feature/observability-metrics`

- ✅ Prometheus metrics defined (counters, histogram, gauge)
- ✅ Tracing context manager with correlation IDs
- ✅ Dual recording (Prometheus + Database)
- ✅ Configuration settings for privacy/compliance
- ✅ Structured logging (TRACE_START/TRACE_END)
- ✅ Non-blocking async DB persistence

**Files Created:**
- `src/core/services/prometheus_metrics_service.py` - Prometheus metric definitions
- `src/core/services/observability_service.py` - Tracing context manager

**Files Modified:**
- `src/core/config.py` - Added observability settings
- `pyproject.toml` - Added `prometheus-client` dependency

**Key Features:**
- `trace_tool_execution()` context manager wraps every tool call
- Automatic correlation ID generation for E2E tracing
- Privacy controls (can disable logging of inputs/outputs)
- Respects feature flags (can disable metrics or DB logging)

---

## Phase 3: Integration (CURRENT - NOT STARTED)

### 3.1 Integrate with Dynamic Tool Loader

**File**: `src/mcp_servers/common/dynamic_loader.py`

**Tasks:**
- [ ] Import `trace_tool_execution` from observability module
- [ ] Update `load_tools_from_db()` signature to accept `domain` and `transport` parameters
- [ ] Wrap all tool wrappers with `trace_tool_execution()`:
  - `echo_wrapper`
  - `add_wrapper`
  - `divide_wrapper`
  - `get_system_info_wrapper`
- [ ] Pass correct domain/transport to each tool wrapper
- [ ] Test that tools still work correctly
- [ ] Verify metrics are being collected

**Example transformation:**
```python
# BEFORE
async def divide_wrapper(a: int, b: int) -> dict[str, Any]:
    """Divide two numbers."""
    try:
        result = handler_func({"a": a, "b": b})
        return result
    except Exception as e:
        logger.error(f"Tool divide failed: {e}")
        return {"success": False, "error": str(e)}

# AFTER
async def divide_wrapper(a: int, b: int) -> dict[str, Any]:
    """Divide two numbers."""
    with trace_tool_execution(
        tool_name="divide",
        parameters={"a": a, "b": b},
        domain=domain,
        transport=transport,
    ):
        try:
            result = handler_func({"a": a, "b": b})
            return result
        except Exception as e:
            logger.error(f"Tool divide failed: {e}")
            return {"success": False, "error": str(e)}
```

**Dependencies**: Phase 2

**Estimated Time**: 2 hours

---

### 3.2 Update STDIO Runner

**File**: `src/mcp_servers/common/stdio_runner.py`

**Tasks:**
- [ ] Import `PROMETHEUS_METRICS` and call `set_server_info()` at startup
- [ ] Pass `transport="stdio"` to `load_tools_from_db()`
- [ ] Ensure domain is passed through correctly
- [ ] Test STDIO mode with metrics collection
- [ ] Verify logs show TRACE_START/TRACE_END

**Dependencies**: 3.1

**Estimated Time**: 30 minutes

---

### 3.3 Update HTTP Runner

**File**: `src/mcp_servers/common/http_runner.py`

**Tasks:**
- [ ] Import `PROMETHEUS_METRICS` and call `set_server_info()` at startup
- [ ] Pass `transport="http"` to `load_tools_from_db()`
- [ ] Ensure domain is passed through correctly
- [ ] Consider extracting session_id from HTTP headers if available
- [ ] Test HTTP streaming mode with metrics collection

**Dependencies**: 3.1

**Estimated Time**: 30 minutes

---

### 3.4 Add Prometheus Metrics Endpoint

**File**: `src/mcp_servers/common/http_runner.py` (or new `src/api/main.py`)

**Tasks:**
- [ ] Import `prometheus_client.generate_latest` and `CONTENT_TYPE_LATEST`
- [ ] Add `/metrics` endpoint to FastAPI app
- [ ] Return Prometheus exposition format
- [ ] Test endpoint returns valid Prometheus metrics
- [ ] Document how to access metrics

**Example:**
```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

**Dependencies**: 3.2, 3.3

**Estimated Time**: 30 minutes

---

## Phase 4: Error Pattern Detection

### 4.1 Create Error Analysis Service

**File**: `src/core/services/error_analysis.py`

**Tasks:**
- [ ] Create `ErrorPatternDetector` class
- [ ] Implement `__init__(repository: ToolExecutionRepository)`
- [ ] Implement `get_error_breakdown(tool_name: str | None, hours: int) -> dict`:
  - Query errors grouped by error_type and error_message
  - Calculate percentages
  - Return top 5 examples per error type
  - Include top failing tools
- [ ] Implement `_get_top_failing_tools(start_time: datetime, limit: int) -> list[dict]`:
  - Query tools with highest error rates
  - Sort by error_rate_pct, then absolute error count
  - Return tool_name, total_calls, error_count, error_rate_pct
- [ ] Implement `detect_anomalies(tool_name: str, window_hours: int, baseline_hours: int) -> dict`:
  - Compare recent window to baseline period
  - Detect error rate spikes (>2x increase = anomaly)
  - Detect latency spikes (>1.5x increase = anomaly)
  - Assign severity levels (high/medium)
  - Return list of anomalies with details
- [ ] Implement `get_error_trends(tool_name: str | None, days: int) -> dict`:
  - Group errors by day
  - Calculate daily error rates
  - Identify trending error types
- [ ] Add docstrings with usage examples

**Dependencies**: Phase 1 (Repository)

**Estimated Time**: 2.5 hours

---

## Phase 5: Metrics API Endpoints (OPTIONAL)

### 5.1 Create Metrics Router (FastAPI)

**File**: `src/api/routers/metrics.py` (new file)

**Tasks:**
- [ ] Create FastAPI router: `router = APIRouter(prefix="/api/metrics", tags=["metrics"])`
- [ ] Implement `GET /api/metrics/tools/{tool_name}`:
  - Return detailed metrics for specific tool
  - Include both real-time (Prometheus) and historical (DB) data
  - Query DB for last 24 hours
  - Calculate success rate, avg duration, error breakdown
- [ ] Implement `GET /api/metrics/dashboard`:
  - Query params: `tool_name`, `window_minutes`
  - Return comprehensive dashboard data
  - Use `ErrorPatternDetector` for error analysis
- [ ] Implement `GET /api/metrics/health`:
  - Return overall system health
  - Include: total tools, total executions, error rates, p95 latency
  - Mark unhealthy if: error rate > 10% or p95 > threshold
- [ ] Add response models (Pydantic schemas) for all endpoints
- [ ] Add OpenAPI documentation with examples

**Note:** This is optional since Prometheus + Grafana provide similar functionality

**Dependencies**: Phase 4

**Estimated Time**: 3 hours

---

## Phase 6: Testing

### 6.1 Unit Tests - Prometheus Metrics

**File**: `tests/unit/services/test_prometheus_metrics.py`

**Tasks:**
- [ ] Test `record_tool_call()`:
  - Verify counters increment
  - Verify histogram records observations
  - Test with success and error status
- [ ] Test `start_tool_execution()` and `end_tool_execution()`:
  - Verify gauge increments/decrements
  - Test concurrent executions
- [ ] Test metric labels are applied correctly
- [ ] Test with different tools, domains, transports

**Dependencies**: Phase 2

**Estimated Time**: 1.5 hours

---

### 6.2 Unit Tests - Tracing Context Manager

**File**: `tests/unit/services/test_observability.py`

**Tasks:**
- [ ] Test `trace_tool_execution()` success path:
  - Verify correlation_id generated
  - Verify TRACE_START/TRACE_END logged
  - Verify context dict has correct fields
- [ ] Test error path:
  - Verify error_type captured
  - Verify error_message captured
  - Verify exception re-raised
  - Verify status="error"
- [ ] Test with provided correlation_id and session_id
- [ ] Test `generate_correlation_id()` returns valid UUID
- [ ] Mock Prometheus metrics to verify calls
- [ ] Mock database to verify persistence attempted

**Dependencies**: Phase 2

**Estimated Time**: 2 hours

---

### 6.3 Integration Tests - E2E Tracing

**File**: `tests/integration/test_observability_integration.py`

**Tasks:**
- [ ] Test full tool execution with tracing:
  - Call actual tool (e.g., echo)
  - Verify execution recorded in DB
  - Verify correlation_id in DB matches logs
  - Query execution by correlation_id
- [ ] Test Prometheus metrics updated:
  - Check counter incremented
  - Check histogram has observation
  - Check gauge returns to 0
- [ ] Test error scenarios:
  - Tool raises exception
  - Verify error recorded in DB
  - Verify error counter incremented
- [ ] Test session_id tracking (multiple calls in same session)
- [ ] Test with `enable_metrics=False` (metrics not recorded)
- [ ] Test with `enable_execution_logging=False` (DB not written)

**Dependencies**: Phase 3

**Estimated Time**: 2 hours

---

### 6.4 Integration Tests - Metrics Endpoint

**File**: `tests/integration/test_metrics_endpoint.py`

**Tasks:**
- [ ] Test `GET /metrics` endpoint:
  - Returns valid Prometheus exposition format
  - Includes expected metric names
  - Contains HELP and TYPE comments
- [ ] Test metrics accumulate correctly:
  - Call tool multiple times
  - Verify counter increases
  - Verify histogram updates
- [ ] Test with TestClient from FastAPI
- [ ] Test metric labels filter correctly

**Dependencies**: Phase 3.4

**Estimated Time**: 1 hour

---

## Phase 7: Documentation & Cleanup

### 7.1 Update Documentation

**Tasks:**
- [ ] Create `docs/OBSERVABILITY.md`:
  - Overview of observability features
  - Prometheus metrics available
  - How to access `/metrics` endpoint
  - Example PromQL queries for common scenarios
  - Grafana dashboard setup guide
  - Database queries for debugging
  - Troubleshooting guide
- [ ] Update `docs/ARCHITECTURE.md`:
  - Add observability layer to architecture diagram
  - Explain hybrid approach (Prometheus + DB)
  - Document tracing flow with diagram
- [ ] Update `docs/DATABASE.md`:
  - Add `tool_executions` table schema
  - Document indexes and their purpose
  - Add example SQL queries for metrics
  - Document retention policy
- [ ] Update `CLAUDE.md`:
  - Add observability section
  - Document how to view metrics
  - Add troubleshooting commands
  - Update "Critical Constraints" if needed
- [ ] Update `README.md`:
  - Add observability feature to feature list
  - Add `/metrics` endpoint example
  - Link to detailed docs
  - Add Grafana dashboard screenshot (optional)

**Dependencies**: All previous phases

**Estimated Time**: 3 hours

---

### 7.2 Add Database Maintenance Scripts

**File**: `scripts/cleanup_old_executions.py`

**Tasks:**
- [ ] Create script to delete executions older than retention period
- [ ] Use `metrics_retention_days` from config
- [ ] Log number of records deleted
- [ ] Add dry-run mode
- [ ] Add to cron job documentation

**File**: `scripts/db.sh` (update)

**Tasks:**
- [ ] Add `executions` command - list recent executions
- [ ] Add `executions-count` command - count by status
- [ ] Add `executions-clean` command - run cleanup script
- [ ] Add `metrics` command - show quick metrics summary

**Dependencies**: Phase 1

**Estimated Time**: 1.5 hours

---

### 7.3 Add Prometheus Configuration Examples

**File**: `config/prometheus/prometheus.yml`

**Tasks:**
- [ ] Create example Prometheus config
- [ ] Configure scrape for MCP server
- [ ] Add recording rules for common queries
- [ ] Add alerting rules examples:
  - High error rate alert
  - High latency alert
  - Tool down alert
- [ ] Document how to run Prometheus locally

**File**: `config/prometheus/alerts.yml`

**Tasks:**
- [ ] Define alert rules:
  - `HighErrorRate` - Error rate > 5% for 5 minutes
  - `HighLatency` - p95 latency > 1s for 5 minutes
  - `ToolDown` - No calls for 10 minutes
- [ ] Add severity labels (critical, warning)
- [ ] Add runbook URLs

**Dependencies**: Phase 3.4

**Estimated Time**: 2 hours

---

## Phase 8: Optional Enhancements

### 8.1 Grafana Dashboard

**File**: `config/grafana/mcp_server_dashboard.json`

**Tasks:**
- [ ] Create Grafana dashboard JSON
- [ ] Add panels for:
  - Request rate (queries per second) - Line graph
  - Error rate percentage - Line graph with threshold
  - p50/p95/p99 latency - Multi-line graph
  - Top 10 tools by request count - Bar chart
  - Top failing tools - Table
  - Error type breakdown - Pie chart
  - In-progress requests - Gauge
- [ ] Add time range selector
- [ ] Add tool filter variable
- [ ] Add domain filter variable
- [ ] Document how to import dashboard
- [ ] Include screenshot in docs

**Dependencies**: Phase 7.3 (Prometheus setup)

**Estimated Time**: 3 hours

---

### 8.2 Real-time Alerting Integration

**File**: `src/core/services/alerting.py`

**Tasks:**
- [ ] Create `AlertManager` class
- [ ] Define alert rules:
  - Error rate > threshold
  - p95 latency > threshold
  - Tool down (no calls in X minutes)
- [ ] Implement alert destinations:
  - Log file
  - Webhook (Slack, PagerDuty, Discord)
  - Email (SMTP)
- [ ] Add alert suppression (don't spam)
- [ ] Add alert resolution tracking
- [ ] Test alert triggering

**Note:** This duplicates Prometheus Alertmanager functionality. Only needed if you want application-level alerting without Prometheus infrastructure.

**Dependencies**: Phase 4

**Estimated Time**: 4 hours

---

### 8.3 Performance Benchmarks

**File**: `tests/performance/test_observability_overhead.py`

**Tasks:**
- [ ] Benchmark tool execution with vs without tracing
- [ ] Measure overhead of:
  - Prometheus recording (~microseconds)
  - Database persistence (async, shouldn't add overhead)
  - Logging (minimal)
- [ ] Target: <1% overhead for tracing
- [ ] Document results

**Dependencies**: Phase 3

**Estimated Time**: 2 hours

---

## Summary

### Total Estimated Time

| Phase | Status | Original Estimate | Revised Estimate | Actual |
|-------|--------|------------------|------------------|--------|
| Phase 1: Database | ✅ Complete | 4.25 hours | 4.25 hours | ~3 hours |
| Phase 2: Instrumentation | ✅ Complete | 6 hours | 3.5 hours | ~2 hours |
| Phase 3: Integration | ⏳ Current | 3 hours | 3.5 hours | - |
| Phase 4: Error Analysis | 📋 Pending | 2.5 hours | 2.5 hours | - |
| Phase 5: API Endpoints | 📋 Optional | 5.5 hours | 3 hours | - |
| Phase 6: Testing | 📋 Pending | 12.5 hours | 6.5 hours | - |
| Phase 7: Documentation | 📋 Pending | 6.5 hours | 6.5 hours | - |
| Phase 8: Optional | 📋 Optional | 9 hours | 9 hours | - |
| **Total** | - | **49.25 hours** | **38.75 hours** | **~5 hours** |

**Time Saved by Using Prometheus:** ~10.5 hours
- Eliminated custom MetricsCollector implementation
- No need to build Prometheus exporter separately
- Reduced testing complexity
- Standard tooling reduces documentation needs

### Minimum Viable Product (MVP)

To get basic observability working with Prometheus:
- ✅ Phase 1: Database (DONE)
- ✅ Phase 2: Instrumentation (DONE)
- ⏳ Phase 3: Integration (~3.5 hours)
- Phase 6.1-6.3: Core tests (~5.5 hours)
- Phase 7.3: Prometheus config (~2 hours)

**MVP Time Remaining: ~11 hours**

### Production Ready

For production deployment with monitoring and alerting:
- MVP (above)
- Phase 4: Error Analysis (~2.5 hours)
- Phase 7: Full Documentation (~6.5 hours)
- Phase 8.1: Grafana Dashboard (~3 hours)

**Production Total: ~23 hours from current state**

### Key Architecture Decisions

✅ **Prometheus for operational metrics** - Industry standard, proven at scale
✅ **PostgreSQL for audit trail** - Structured queries, long retention
✅ **Async DB writes** - Don't slow down tool execution
✅ **Privacy controls** - Can disable logging of sensitive data
✅ **Feature flags** - Can disable metrics or logging independently
✅ **Correlation IDs** - E2E tracing across multiple tools

### Next Steps

1. **Review this updated plan** - Ensure it aligns with your vision
2. **Commit Phase 2** - Save the Prometheus instrumentation
3. **Start Phase 3** - Integrate tracing into tool wrappers
4. **Test locally** - Verify `/metrics` endpoint works
5. **Add Prometheus locally** - Test scraping and queries
6. **Create Grafana dashboard** - Visualize metrics

# Observability & Metrics Implementation Plan

## Overview

This document outlines the detailed implementation plan for adding comprehensive observability and metrics to the MCP server blueprint. The implementation follows a phased approach to ensure each component can be tested independently before integration.

## Goals

- ✅ Track execution count per tool
- ✅ Calculate success/failure rates
- ✅ Measure average execution time and percentile latencies (p50, p75, p90, p95, p99)
- ✅ Identify error patterns and anomalies
- ✅ Enable E2E tracing with correlation_id/session_id
- ✅ Export system metrics (counters, timers, per-tool breakdown)
- ✅ Provide real-time and historical metrics

## Architecture

### Dual-Layer Approach

1. **In-Memory Metrics Collector** (Real-time)
   - Sliding window calculations for percentiles
   - Time-bucketed counters for rate calculations
   - Fast access for live dashboards
   - Thread-safe operations

2. **Database Storage** (Historical)
   - Persistent audit trail of all executions
   - Long-term trend analysis
   - Complex queries and aggregations
   - Compliance and debugging

## Implementation Phases

---

## Phase 1: Database Foundation

### 1.1 Create Migration for `tool_executions` Table

**File**: `migrations/versions/XXX_add_tool_executions.py`

**Tasks**:
- [ ] Create Alembic migration file
- [ ] Define table schema with columns:
  - `id` (primary key)
  - `tool_name` (indexed, varchar 100)
  - `correlation_id` (indexed, uuid/varchar 36)
  - `session_id` (indexed, nullable, uuid/varchar 36)
  - `started_at` (indexed, timestamp)
  - `completed_at` (nullable, timestamp)
  - `duration_ms` (nullable, float)
  - `status` (varchar 20: success, error, timeout)
  - `error_type` (nullable, varchar 100)
  - `error_message` (nullable, text)
  - `input_params` (nullable, jsonb)
  - `output_data` (nullable, jsonb)
  - `transport` (varchar 20: stdio, http, rest)
  - `domain` (varchar 50: general, kubernetes, etc.)
- [ ] Add indexes:
  - `idx_tool_executions_tool_name` on `tool_name`
  - `idx_tool_executions_correlation_id` on `correlation_id`
  - `idx_tool_executions_session_id` on `session_id`
  - `idx_tool_executions_started_at` on `started_at`
  - `idx_tool_executions_status` on `status`
- [ ] Add composite index: `idx_tool_executions_tool_status_time` on `(tool_name, status, started_at)`
- [ ] Test migration up/down

**Dependencies**: None

**Estimated Time**: 1 hour

---

### 1.2 Create SQLAlchemy Model

**File**: `src/core/models/tool_execution.py`

**Tasks**:
- [ ] Create `ToolExecution` class extending `Base`
- [ ] Define all mapped columns with proper types
- [ ] Add `__repr__` method for debugging
- [ ] Add property methods:
  - `is_success` -> bool
  - `is_error` -> bool
  - `duration_seconds` -> float | None
- [ ] Add validation constraints (e.g., status must be in allowed values)
- [ ] Import in `src/core/models/__init__.py`

**Dependencies**: 1.1

**Estimated Time**: 45 minutes

---

### 1.3 Create Repository Layer

**File**: `src/core/repositories/tool_execution_repository.py`

**Tasks**:
- [ ] Create `ToolExecutionRepository` class
- [ ] Implement CRUD operations:
  - `create(execution_data: dict) -> ToolExecution`
  - `get_by_id(execution_id: int) -> ToolExecution | None`
  - `get_by_correlation_id(correlation_id: str) -> list[ToolExecution]`
  - `get_by_session_id(session_id: str) -> list[ToolExecution]`
- [ ] Implement query methods:
  - `get_recent_by_tool(tool_name: str, limit: int = 100) -> list[ToolExecution]`
  - `get_by_time_range(start: datetime, end: datetime, tool_name: str | None) -> list[ToolExecution]`
  - `count_by_status(tool_name: str | None, start: datetime | None) -> dict[str, int]`
- [ ] Implement metric calculation methods:
  - `get_tool_stats(tool_name: str, start_time: datetime, end_time: datetime) -> dict`
  - `get_percentile_latencies(tool_name: str | None, start_time: datetime | None, end_time: datetime | None) -> dict`
  - `get_historical_rates(tool_name: str | None, start_time: datetime | None, end_time: datetime | None, bucket_size_minutes: int) -> list[dict]`
- [ ] Add helper method: `_percentile(sorted_values: list[float], p: int) -> float`
- [ ] Import in `src/core/repositories/__init__.py`

**Dependencies**: 1.2

**Estimated Time**: 2 hours

---

## Phase 2: Core Instrumentation

### 2.1 Create Metrics Collector

**File**: `src/core/services/metrics.py`

**Tasks**:
- [ ] Create `MetricsCollector` class with thread-safe operations
- [ ] Initialize data structures:
  - `_lock: threading.Lock`
  - `_counters: dict[str, int]` (lifetime counters)
  - `_latency_windows: dict[str, deque[tuple[datetime, float]]]` (sliding window for percentiles)
  - `_time_buckets: dict[str, deque[tuple[datetime, int]]]` (bucketed for rates)
  - `_last_reset: datetime`
- [ ] Implement `record_execution(tool_name: str, context: dict) -> None`:
  - Update counters (total, per-status, per-error-type)
  - Append to latency window (maxlen=1000)
  - Increment time buckets
- [ ] Implement `get_percentiles(tool_name: str | None, window_seconds: int) -> dict`:
  - Filter latency window to time range
  - Calculate p50, p75, p90, p95, p99, max
  - Return count and window_seconds
- [ ] Implement `get_rates(tool_name: str | None) -> dict`:
  - Calculate rates for 5s, 30s, 60s windows
  - Return calls/sec, success/sec, error/sec for each window
- [ ] Implement `get_counters(tool_name: str | None) -> dict`:
  - Return lifetime counters (total calls, successes, errors by type)
- [ ] Implement helper methods:
  - `_increment_time_bucket(metric_key: str, timestamp: datetime) -> None`
  - `_sum_buckets(metric_key: str, cutoff: datetime) -> int`
  - `_percentile(sorted_values: list[float], p: int) -> float`
  - `_get_global_rates(now: datetime) -> dict` (aggregate across all tools)
- [ ] Create singleton instance: `METRICS_COLLECTOR = MetricsCollector()`
- [ ] Add `reset_metrics()` method for testing

**Dependencies**: None

**Estimated Time**: 3 hours

---

### 2.2 Create Tracing Context Manager

**File**: `src/core/services/observability.py`

**Tasks**:
- [ ] Import dependencies (uuid, datetime, asyncio, logging, contextmanager)
- [ ] Create `trace_tool_execution()` context manager:
  - Parameters: `tool_name`, `parameters`, `domain`, `transport`, `correlation_id`, `session_id`
  - Generate correlation_id if not provided (uuid4)
  - Initialize trace context dict with: correlation_id, session_id, started_at
  - Log TRACE_START with structured fields
  - Yield context to caller
  - In except block: capture error_type, error_message, set status="error", re-raise
  - In finally block:
    - Set completed_at
    - Calculate duration_ms
    - Log TRACE_END with duration and status
    - Call `_persist_execution_async()` to save to DB
    - Call `METRICS_COLLECTOR.record_execution()`
- [ ] Implement `_persist_execution_async()`:
  - Use `asyncio.create_task()` to avoid blocking
  - Create new DB session
  - Call `ToolExecutionRepository.create()`
  - Handle exceptions with error logging
  - Close session properly
- [ ] Add helper functions:
  - `generate_correlation_id() -> str`
  - `get_correlation_id_from_context() -> str | None` (placeholder for MCP context integration)
  - `get_session_id_from_context() -> str | None` (placeholder for MCP context integration)
- [ ] Configure structured logging format for TRACE_START/TRACE_END

**Dependencies**: 1.3, 2.1

**Estimated Time**: 2 hours

---

### 2.3 Update Configuration

**File**: `src/core/config.py`

**Tasks**:
- [ ] Add observability settings to `Settings` class:
  - `enable_metrics: bool = True`
  - `enable_execution_logging: bool = True`
  - `metrics_retention_days: int = 30`
  - `log_tool_inputs: bool = False` (PII concern)
  - `log_tool_outputs: bool = False` (PII concern)
  - `max_latency_samples: int = 1000`
- [ ] Add environment variable mappings
- [ ] Document settings in docstring

**Dependencies**: None

**Estimated Time**: 30 minutes

---

## Phase 3: Integration

### 3.1 Integrate with Dynamic Tool Loader

**File**: `src/mcp_servers/common/dynamic_loader.py`

**Tasks**:
- [ ] Import `trace_tool_execution` from observability module
- [ ] Import `get_settings` to check if metrics enabled
- [ ] For each tool wrapper in `register_tool_from_db()`, wrap execution with tracing:
  - Add `domain` parameter to `load_tools_from_db()` function
  - Add `transport` parameter to `load_tools_from_db()` function
  - Pass these to trace context manager
- [ ] Update all existing tool wrappers (echo, add, divide, get_system_info):
  ```python
  async def tool_wrapper(...) -> dict[str, Any]:
      """Tool description."""
      with trace_tool_execution(
          tool_name=tool.name,
          parameters={"param": param},  # Match wrapper signature
          domain=domain,
          transport=transport,
      ):
          try:
              result = handler_func({"param": param})
              return result
          except Exception as e:
              logger.error(f"Tool {tool.name} failed: {e}")
              return {"success": False, "error": str(e)}
  ```
- [ ] Test that existing tools still work correctly
- [ ] Verify metrics are being collected

**Dependencies**: 2.2

**Estimated Time**: 2 hours

---

### 3.2 Update STDIO Runner

**File**: `src/mcp_servers/common/stdio_runner.py`

**Tasks**:
- [ ] Pass `transport="stdio"` to `load_tools_from_db()`
- [ ] Ensure domain is passed through correctly
- [ ] Test STDIO mode with metrics collection

**Dependencies**: 3.1

**Estimated Time**: 30 minutes

---

### 3.3 Update HTTP Runner

**File**: `src/mcp_servers/common/http_runner.py`

**Tasks**:
- [ ] Pass `transport="http"` to `load_tools_from_db()`
- [ ] Ensure domain is passed through correctly
- [ ] Consider extracting session_id from HTTP headers if available
- [ ] Test HTTP streaming mode with metrics collection

**Dependencies**: 3.1

**Estimated Time**: 30 minutes

---

## Phase 4: Error Pattern Detection

### 4.1 Create Error Analysis Service

**File**: `src/core/services/error_analysis.py`

**Tasks**:
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

**Dependencies**: 1.3

**Estimated Time**: 2.5 hours

---

## Phase 5: Metrics API Endpoints

### 5.1 Create Metrics Router (FastAPI)

**File**: `src/api/routers/metrics.py` (new file)

**Tasks**:
- [ ] Create FastAPI router: `router = APIRouter(prefix="/metrics", tags=["metrics"])`
- [ ] Implement `GET /metrics`:
  - Return Prometheus-style text format
  - Include: `METRICS_COLLECTOR.get_metrics()`
  - Format as `# TYPE` and `metric_name value` lines
- [ ] Implement `GET /metrics/json`:
  - Return JSON format of all metrics
  - Include counters, percentiles, rates
- [ ] Implement `GET /metrics/tools/{tool_name}`:
  - Return detailed metrics for specific tool
  - Include both real-time and historical data
  - Query DB for last 24 hours
  - Calculate success rate, avg duration, error breakdown
- [ ] Implement `GET /metrics/dashboard`:
  - Query params: `tool_name`, `window_minutes`
  - Return comprehensive dashboard data:
    - Live metrics (rates, percentiles, counters)
    - Historical metrics (time series, error breakdown)
    - Anomalies (if tool_name specified)
  - Use `ErrorPatternDetector` for error analysis
- [ ] Implement `GET /metrics/health`:
  - Return overall system health
  - Include: total tools, total executions, error rates, p95 latency
  - Mark unhealthy if: error rate > 10% or p95 > threshold
- [ ] Add response models (Pydantic schemas) for all endpoints
- [ ] Add OpenAPI documentation with examples

**Dependencies**: 2.1, 4.1

**Estimated Time**: 3 hours

---

### 5.2 Create Response Schemas

**File**: `src/core/schemas/metrics.py` (new file)

**Tasks**:
- [ ] Create `MetricsSummaryResponse` schema:
  - counters: dict[str, int]
  - histograms: dict[str, PercentileMetrics]
  - uptime_seconds: float
- [ ] Create `PercentileMetrics` schema:
  - count, sum, mean, p50, p75, p90, p95, p99, max
- [ ] Create `RateMetrics` schema:
  - rate_5s, rate_30s, rate_60s (calls per second)
- [ ] Create `ToolMetricsResponse` schema:
  - tool_name, total_executions, success_rate
  - avg_duration_ms, p95_duration_ms
  - error_breakdown: dict[str, int]
  - recent_errors: list[ErrorDetail]
- [ ] Create `ErrorDetail` schema:
  - error_type, error_message, count, first_seen, last_seen
- [ ] Create `DashboardResponse` schema:
  - live: LiveMetrics
  - historical: HistoricalMetrics
  - anomalies: AnomalyReport | None
  - generated_at: datetime
- [ ] Create `AnomalyReport` schema:
  - tool_name, window_hours, anomalies: list[Anomaly], has_anomalies
- [ ] Create `Anomaly` schema:
  - type (error_rate_spike, latency_spike)
  - severity (high, medium, low)
  - current, baseline, ratio
- [ ] Add examples to schemas for OpenAPI docs

**Dependencies**: None

**Estimated Time**: 1.5 hours

---

### 5.3 Integrate Metrics Router into Main App

**File**: `src/api/main.py` (will be created in REST API phase)

**Tasks**:
- [ ] Create basic FastAPI app if doesn't exist
- [ ] Import metrics router
- [ ] Include router: `app.include_router(metrics.router)`
- [ ] Add CORS middleware for browser access
- [ ] Test all metrics endpoints
- [ ] Document how to run REST API server

**Note**: This can be a minimal implementation just for metrics, even before full REST API phase.

**Dependencies**: 5.1, 5.2

**Estimated Time**: 1 hour

---

## Phase 6: Testing

### 6.1 Unit Tests - Metrics Collector

**File**: `tests/unit/services/test_metrics.py`

**Tasks**:
- [ ] Test `record_execution()`:
  - Verify counters increment correctly
  - Verify latency windows store values
  - Verify time buckets created correctly
- [ ] Test `get_percentiles()`:
  - With empty data (returns zeros)
  - With single value
  - With multiple values
  - Test time window filtering
  - Verify p50, p75, p90, p95, p99 calculations
- [ ] Test `get_rates()`:
  - With no data
  - With data in different time windows
  - Verify 5s, 30s, 60s calculations
  - Test both per-tool and global rates
- [ ] Test `get_counters()`:
  - Lifetime counters
  - Per-tool filtering
  - Error type breakdown
- [ ] Test thread safety (concurrent record_execution calls)
- [ ] Test reset_metrics()

**Dependencies**: 2.1

**Estimated Time**: 2 hours

---

### 6.2 Unit Tests - Repository

**File**: `tests/unit/repositories/test_tool_execution_repository.py`

**Tasks**:
- [ ] Test `create()` - verify record saved
- [ ] Test `get_by_id()` - existing and non-existing
- [ ] Test `get_by_correlation_id()` - multiple executions with same ID
- [ ] Test `get_recent_by_tool()` - verify ordering and limit
- [ ] Test `get_tool_stats()`:
  - Calculate success rate correctly
  - Calculate avg duration
  - Handle empty results
- [ ] Test `get_percentile_latencies()`:
  - With various data distributions
  - Filter by tool_name
  - Filter by time range
  - Verify percentile accuracy
- [ ] Test `get_historical_rates()`:
  - Verify bucketing by time
  - Calculate rates per second
  - Handle timezone correctly
- [ ] Use in-memory SQLite for tests
- [ ] Create fixtures for sample execution data

**Dependencies**: 1.3

**Estimated Time**: 2.5 hours

---

### 6.3 Unit Tests - Error Analysis

**File**: `tests/unit/services/test_error_analysis.py`

**Tasks**:
- [ ] Test `get_error_breakdown()`:
  - With no errors (empty result)
  - With multiple error types
  - Verify percentage calculations
  - Verify top 5 examples returned
- [ ] Test `_get_top_failing_tools()`:
  - Verify sorting by error rate
  - Verify limit works
  - Handle tools with 100% error rate
- [ ] Test `detect_anomalies()`:
  - No anomaly (stable metrics)
  - Error rate spike detected
  - Latency spike detected
  - Both anomalies simultaneously
  - Verify severity levels
- [ ] Mock repository responses for isolation
- [ ] Test edge cases (zero baseline, zero recent)

**Dependencies**: 4.1

**Estimated Time**: 2 hours

---

### 6.4 Integration Tests - E2E Tracing

**File**: `tests/integration/test_observability.py`

**Tasks**:
- [ ] Test `trace_tool_execution()` context manager:
  - Successful execution path
  - Error execution path
  - Verify correlation_id generated
  - Verify TRACE_START/TRACE_END logs
  - Verify DB record created
  - Verify metrics collector updated
  - Verify duration calculated correctly
- [ ] Test with actual tool execution:
  - Call echo tool
  - Verify execution recorded in DB
  - Verify correlation_id in logs
  - Query execution by correlation_id
- [ ] Test session_id tracking (multiple calls in same session)
- [ ] Test error scenarios:
  - Handler raises exception
  - Verify error_type and error_message captured
  - Verify status="error"
- [ ] Test async persistence doesn't block tool execution
- [ ] Verify PII redaction if `log_tool_inputs=False`

**Dependencies**: 2.2, 3.1

**Estimated Time**: 2 hours

---

### 6.5 Integration Tests - Metrics API

**File**: `tests/integration/test_metrics_api.py`

**Tasks**:
- [ ] Test `GET /metrics` endpoint:
  - Returns Prometheus format
  - Includes expected metric names
- [ ] Test `GET /metrics/json`:
  - Returns valid JSON
  - Includes counters, percentiles, rates
- [ ] Test `GET /metrics/tools/{tool_name}`:
  - Returns tool-specific metrics
  - 404 for non-existent tool
  - Correct success rate calculation
- [ ] Test `GET /metrics/dashboard`:
  - With and without tool_name
  - Different window_minutes values
  - Verify live and historical data present
  - Verify anomaly detection runs
- [ ] Test `GET /metrics/health`:
  - Healthy state
  - Unhealthy state (high error rate)
- [ ] Use TestClient from FastAPI
- [ ] Seed DB with sample execution data

**Dependencies**: 5.1, 5.3

**Estimated Time**: 2 hours

---

### 6.6 Performance Tests

**File**: `tests/performance/test_metrics_performance.py`

**Tasks**:
- [ ] Test metrics collector performance:
  - Benchmark `record_execution()` (should be <1ms)
  - Test with 10,000 concurrent recordings
  - Verify no memory leaks with sliding windows
- [ ] Test DB insertion performance:
  - Bulk insert 1,000 executions
  - Measure insert time
- [ ] Test query performance:
  - Query percentiles for 1M records
  - Query rates with 1M records
  - Ensure indexes are used (EXPLAIN ANALYZE)
- [ ] Verify async persistence doesn't impact tool latency
- [ ] Profile memory usage over time

**Dependencies**: 2.1, 1.3

**Estimated Time**: 2 hours

---

## Phase 7: Documentation & Cleanup

### 7.1 Update Documentation

**Tasks**:
- [ ] Create `docs/OBSERVABILITY.md`:
  - Overview of observability features
  - Metrics available (counters, rates, percentiles)
  - How to access metrics endpoints
  - Example queries and responses
  - Grafana/Prometheus integration guide
  - Troubleshooting guide
- [ ] Update `docs/ARCHITECTURE.md`:
  - Add observability layer to architecture diagram
  - Explain dual-layer approach (in-memory + DB)
  - Document tracing flow
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
  - Add metrics endpoint example
  - Link to detailed docs

**Dependencies**: All previous phases

**Estimated Time**: 3 hours

---

### 7.2 Add Database Maintenance Scripts

**File**: `scripts/cleanup_old_executions.py`

**Tasks**:
- [ ] Create script to delete executions older than retention period
- [ ] Use `metrics_retention_days` from config
- [ ] Log number of records deleted
- [ ] Add dry-run mode
- [ ] Add to cron job documentation

**File**: `scripts/db.sh` (update)

**Tasks**:
- [ ] Add `executions` command - list recent executions
- [ ] Add `executions-count` command - count by status
- [ ] Add `executions-clean` command - run cleanup script
- [ ] Add `metrics` command - show quick metrics summary

**Dependencies**: 1.1, 1.3

**Estimated Time**: 1.5 hours

---

### 7.3 Add Examples

**File**: `examples/query_metrics.py`

**Tasks**:
- [ ] Example: Query tool metrics programmatically
- [ ] Example: Detect anomalies for a tool
- [ ] Example: Generate daily metrics report
- [ ] Example: Export metrics to CSV
- [ ] Add comprehensive comments

**File**: `examples/visualize_metrics.py` (optional)

**Tasks**:
- [ ] Use matplotlib to create charts
- [ ] Plot latency trends over time
- [ ] Plot error rates by tool
- [ ] Show p95 latency comparison

**Dependencies**: 4.1, 5.1

**Estimated Time**: 2 hours

---

## Phase 8: Optional Enhancements

### 8.1 Prometheus Exporter

**File**: `src/api/routers/prometheus.py`

**Tasks**:
- [ ] Format metrics in Prometheus exposition format
- [ ] Include HELP and TYPE comments
- [ ] Export as `/metrics` endpoint (standard path)
- [ ] Test with actual Prometheus scraper
- [ ] Document Prometheus configuration

**Dependencies**: 5.1

**Estimated Time**: 2 hours

---

### 8.2 Grafana Dashboard

**File**: `config/grafana/dashboard.json`

**Tasks**:
- [ ] Create Grafana dashboard JSON
- [ ] Add panels for:
  - Request rate (queries per second)
  - Error rate
  - p95/p99 latency
  - Top failing tools
  - Error type breakdown
- [ ] Add time range selector
- [ ] Add tool filter variable
- [ ] Document how to import dashboard
- [ ] Include screenshot in docs

**Dependencies**: 8.1

**Estimated Time**: 3 hours

---

### 8.3 Real-time Alerting

**File**: `src/core/services/alerting.py`

**Tasks**:
- [ ] Create `AlertManager` class
- [ ] Define alert rules:
  - Error rate > threshold
  - p95 latency > threshold
  - Tool down (no calls in X minutes)
- [ ] Implement alert destinations:
  - Log file
  - Webhook (Slack, PagerDuty)
  - Email
- [ ] Add alert suppression (don't spam)
- [ ] Add alert resolution tracking
- [ ] Test alert triggering

**Dependencies**: 4.1

**Estimated Time**: 4 hours

---

## Summary

### Total Estimated Time: 46-50 hours

### Phase Breakdown:
- **Phase 1**: Database Foundation - 4.25 hours
- **Phase 2**: Core Instrumentation - 6 hours
- **Phase 3**: Integration - 3 hours
- **Phase 4**: Error Pattern Detection - 2.5 hours
- **Phase 5**: Metrics API Endpoints - 5.5 hours
- **Phase 6**: Testing - 12.5 hours
- **Phase 7**: Documentation & Cleanup - 6.5 hours
- **Phase 8**: Optional Enhancements - 9 hours

### Minimum Viable Product (MVP):
To get basic observability working, complete:
- Phase 1 (Database)
- Phase 2 (Instrumentation)
- Phase 3 (Integration)
- Phase 5.1 (Basic metrics endpoint)
- Phase 6.1-6.4 (Core tests)

**MVP Time: ~20 hours**

### Dependencies Graph:
```
1.1 → 1.2 → 1.3 → 2.2 → 3.1 → 3.2, 3.3
                    ↓
2.1 ────────────→ 5.1 → 5.3
                    ↓
1.3 ────────────→ 4.1 ──┘

Testing phases (6.x) depend on their corresponding implementation phases
Documentation (7.x) depends on all implementation phases
Optional (8.x) can be done anytime after core features
```

### Next Steps:
1. Review this plan and adjust priorities
2. Decide on MVP vs full implementation
3. Create implementation branch
4. Start with Phase 1.1 (database migration)
5. Work through phases sequentially, testing as you go

### Notes:
- All times are estimates for a single developer
- Testing time is generous to ensure quality
- Optional enhancements (Phase 8) can be deferred
- Consider running Phases 6.1-6.5 in parallel with implementation
- Database migration should be reviewed by DBA if in production

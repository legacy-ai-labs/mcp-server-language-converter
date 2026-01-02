# Testing Observability Middleware

This guide shows you how to test that the observability middleware is working correctly.

## Quick Test (No Database Required)

Test that the middleware is properly integrated:

```bash
# 1. Verify imports work
uv run python -c "
from src.mcp_servers.common.observability_middleware import ObservabilityMiddleware
from src.mcp_servers.common.base_server import create_mcp_server
print('✓ Observability middleware imports successfully')

# Create server with middleware
mcp = create_mcp_server(domain='test', transport='stdio')
print('✓ Server created with observability middleware')
"
```

## Full Integration Test (Requires Database)

### Prerequisites

1. **Database Setup**:
   ```bash
   # Create database (adjust username if needed)
   createdb mcp_server

   # Initialize schema
   uv run python scripts/init_db.py

   # Seed tools
   uv run python scripts/seed_tools.py
   ```

2. **Environment Variables** (optional):
   Create a `.env` file:
   ```bash
   # Enable full observability
   enable_metrics=True
   enable_execution_logging=True

   # Enable input/output logging (contains PII!)
   log_tool_inputs=True
   log_tool_outputs=True
   ```

### Automated Test

Run the complete observability test:

```bash
./scripts/test_observability.sh
```

This script will:
1. ✓ Check database connection
2. ✓ Initialize database schema
3. ✓ Seed tools
4. ✓ Run integration test
5. ✓ Verify data was recorded
6. ✓ Show execution statistics

### Manual Test

**Step 1: Check current state**
```bash
./scripts/db.sh query "SELECT COUNT(*) FROM tool_executions;"
```

**Step 2: Run the integration test**
```bash
uv run python scripts/test_observability_integration.py
```

**Step 3: Verify data was created**
```bash
# Show recent executions
./scripts/db.sh query "
SELECT
    tool_name,
    status,
    ROUND(duration_ms::numeric, 2) as duration_ms,
    transport,
    domain,
    to_char(started_at, 'YYYY-MM-DD HH24:MI:SS') as started_at
FROM tool_executions
ORDER BY started_at DESC
LIMIT 10;
"
```

**Step 4: View execution statistics**
```bash
./scripts/db.sh query "
SELECT
    tool_name,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successes,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as errors,
    ROUND(AVG(duration_ms)::numeric, 2) as avg_duration_ms,
    ROUND(MIN(duration_ms)::numeric, 2) as min_duration_ms,
    ROUND(MAX(duration_ms)::numeric, 2) as max_duration_ms
FROM tool_executions
GROUP BY tool_name
ORDER BY total_calls DESC;
"
```

## Testing with Real MCP Server

### STDIO Mode (Claude Desktop)

1. **Start the server** (in one terminal):
   ```bash
   uv run python -m src.mcp_servers.mcp_general 2>&1 | tee server.log
   ```

2. **Watch the logs** for observability traces:
   ```bash
   # In another terminal
   tail -f server.log | grep "TRACE_"
   ```

   You should see:
   ```
   TRACE_START tool=echo domain=general transport=stdio correlation_id=...
   TRACE_END tool=echo correlation_id=... duration_ms=5.23 status=success
   ```

3. **Query the database** to see recorded executions:
   ```bash
   # Watch for new executions in real-time
   watch -n 2 './scripts/db.sh query "SELECT tool_name, status, ROUND(duration_ms::numeric, 2) as duration_ms, started_at FROM tool_executions ORDER BY started_at DESC LIMIT 5;"'
   ```

### HTTP Streaming Mode

1. **Start HTTP server**:
   ```bash
   uv run python -m src.mcp_servers.mcp_general sse
   ```

2. **Check Prometheus metrics** (http://<IP>:9090/metrics):
   ```bash
   curl http://localhost:9090/metrics | grep mcp_tool
   ```

   You should see:
   ```
   mcp_tool_calls_total{domain="general",status="success",tool="echo",transport="sse"} 5.0
   mcp_tool_duration_seconds_bucket{domain="general",tool="echo",transport="sse",le="0.01"} 3.0
   ```

## What to Look For

### ✓ Success Indicators

1. **Database Records Created**:
   - New rows in `tool_executions` table
   - Correlation IDs are UUIDs
   - Duration measured in milliseconds
   - Status is "success" or "error"

2. **Structured Logs**:
   - `TRACE_START` before tool execution
   - `TRACE_END` after tool execution
   - Correlation ID matches between START and END

3. **Prometheus Metrics** (if enabled):
   - `mcp_tool_calls_total` increments
   - `mcp_tool_duration_seconds` records latency
   - `mcp_tool_in_progress` shows current load

### ✗ Failure Indicators

1. **No Database Records**:
   - Check: `enable_execution_logging=True` in config
   - Check: Database connection is working
   - Check logs for "event loop mismatch" warnings

2. **No Metrics**:
   - Check: `enable_metrics=True` in config
   - Check: Prometheus client library is installed

3. **Missing Logs**:
   - Check: Log level is INFO or DEBUG
   - Check: Logging to stderr (default)

## Troubleshooting

### Event Loop Mismatch

If you see warnings like:
```
Cannot persist execution: event loop mismatch
```

This is **expected** with FastMCP's anyio-based transports. The middleware still works, but database persistence might fail. Prometheus metrics will still be recorded.

**Solution**: This is a known limitation. Metrics are still tracked successfully.

### Database Connection Errors

```
psycopg2.OperationalError: connection to server failed
```

**Solution**:
1. Check PostgreSQL is running: `pg_isready`
2. Verify connection string in `.env`:
   ```bash
   database_url=postgresql+asyncpg://postgres:postgres@localhost:5432/mcp_server
   ```

### Import Errors

```
ModuleNotFoundError: No module named 'fastmcp.server.middleware'
```

**Solution**: Update FastMCP to 2.9+:
```bash
uv add "fastmcp>=2.9.0"
uv sync
```

## Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `enable_metrics` | `True` | Enable Prometheus metrics |
| `enable_execution_logging` | `True` | Enable database logging |
| `log_tool_inputs` | `False` | Store input parameters (PII concern) |
| `log_tool_outputs` | `False` | Store output data (PII concern) |
| `metrics_retention_days` | `30` | Database retention period |

## Example Output

**Database Record:**
```sql
tool_executions:
  tool_name: "echo"
  correlation_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  status: "success"
  duration_ms: 5.23
  transport: "stdio"
  domain: "general"
  started_at: 2024-01-15 10:30:45.123
  completed_at: 2024-01-15 10:30:45.128
```

**Log Output:**
```
TRACE_START tool=echo domain=general transport=stdio correlation_id=a1b2c3d4...
TRACE_END tool=echo correlation_id=a1b2c3d4... duration_ms=5.23 status=success
```

**Prometheus Metrics:**
```
mcp_tool_calls_total{domain="general",status="success",tool="echo",transport="stdio"} 1.0
mcp_tool_duration_seconds_sum{domain="general",tool="echo",transport="stdio"} 0.00523
mcp_tool_duration_seconds_count{domain="general",tool="echo",transport="stdio"} 1.0
```

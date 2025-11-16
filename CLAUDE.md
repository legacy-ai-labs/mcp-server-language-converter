# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A hybrid MCP server blueprint demonstrating **Hexagonal Architecture** - implementing business logic once and exposing it through multiple transport layers:
- **MCP STDIO** (Claude Desktop, Cursor IDE)
- **MCP HTTP Streaming** (web-based AI clients)
- **REST API** (traditional web apps) - planned

**Core architectural principle**: Business logic in `src/core/` is transport-agnostic and shared by all interfaces.

## Critical Architecture Concepts

### Shared Infrastructure Pattern

All domain-specific servers share common infrastructure in `mcp_servers/common/`:

```
mcp_servers/
├── common/                      # Shared infrastructure (NO duplication!)
│   ├── base_server.py          # FastMCP initialization
│   ├── dynamic_loader.py       # DB tool loading with wrapper registration
│   ├── stdio_runner.py         # Generic STDIO transport
│   └── http_runner.py          # Generic HTTP streaming transport
│
├── mcp_general/                # Domain-specific servers (minimal code)
│   ├── __main__.py             # 7 lines: run_stdio_server(domain="general")
│   └── http_main.py            # 7 lines: run_http_server(domain="general")
│
├── mcp_kubernetes/             # Placeholder: Same pattern (not yet implemented)
├── mcp_os_commands/            # Placeholder: Same pattern (not yet implemented)
└── mcp_shopping/               # Placeholder: Same pattern (not yet implemented)
```

**Key benefit**: Adding a new domain server requires only **14 lines of code** (2 files × 7 lines each).

### Dynamic Tool Loading System

Tools are **database-driven** with a 4-part registration flow:

1. **Handler Function** (`src/core/services/tool_handlers_service.py`): Pure business logic
   ```python
   def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
       """Business logic for my_tool."""
       return {"success": True, "result": parameters.get("input")}
   ```

2. **Handler Registry** (`TOOL_HANDLERS` dict in same file): Maps names to functions
   ```python
   TOOL_HANDLERS = {
       # ... existing handlers
       "my_tool_handler": my_tool_handler,
   }
   ```

3. **Database Record** (`scripts/seed_tools.py`): Metadata with parameters schema
   ```python
   ToolCreate(
       name="my_tool",
       description="Does X",
       handler_name="my_tool_handler",
       parameters_schema={
           "type": "object",
           "properties": {
               "input": {"type": "string", "description": "Input text"}
           },
           "required": ["input"]
       },
       category="utility",
       domain="general",
       is_active=True
   )
   ```

4. **Wrapper Function** (`src/mcp_servers/common/dynamic_loader.py`): FastMCP tool registration with observability
   ```python
   # In register_tool_from_db function, add:
   elif tool.name == "my_tool":
       async def my_tool_wrapper(input: str) -> dict[str, Any]:
           """Does X."""
           with trace_tool_execution(
               tool_name=tool.name,
               parameters={"input": input},
               domain=domain,
               transport=transport,
           ):
               try:
                   result = handler_func({"input": input})
                   return result
               except Exception as e:
                   logger.error(f"Tool {tool.name} failed: {e}")
                   return {"success": False, "error": str(e)}

       decorated_tool = mcp.tool(name=tool.name, description=tool.description)(my_tool_wrapper)
   ```

**Current limitation**: Each tool requires a specific wrapper function because FastMCP needs explicit parameter signatures. A future enhancement could use dynamic signature generation.

**Observability**: All tool wrappers are automatically traced with `trace_tool_execution()` context manager, which:
- Records metrics to Prometheus (request counts, latency, errors)
- Logs execution to database for audit trail and debugging
- Generates correlation IDs for E2E tracing
- Provides structured logging (TRACE_START/TRACE_END)

**Startup sequence**: Tools loaded from DB **before** `mcp.run()` - handled automatically by runners in `common/`. Prometheus metrics are initialized at startup.

### Multi-Server Architecture

This blueprint supports **multiple domain-specific servers** (general, kubernetes, os_commands, shopping). Each loads tools filtered by `domain` field from the database.

**Current status**: Only `mcp_general` is fully implemented. The other domain servers (`mcp_kubernetes`, `mcp_os_commands`, `mcp_shopping`) are directory placeholders to demonstrate the pattern.

This pattern is useful for:
- **Security boundaries** (different permission levels)
- **Independent scaling** (scale high-traffic domains separately)
- **Team ownership** (different teams own different domains)

**Note**: Most real-world MCP servers use a single server with many tools. Use multiple servers only when you need the benefits above.

### COBOL Analysis Domain (Work in Progress)

This project includes a specialized domain for **COBOL reverse engineering** that demonstrates advanced tool implementation:

**Location**: `src/mcp_servers/mcp_cobol_analysis/`

**Key Features**:
- Control Flow Graph (CFG) generation from COBOL code
- Data Flow Graph (DFG) analysis
- AST (Abstract Syntax Tree) building
- COBOL parser integration using PLY (Python Lex-Yacc)

**Services**:
- `cfg_builder_service.py` - Control flow analysis (`src/core/services/cfg_builder_service.py`)
- `dfg_builder_service.py` - Data flow analysis (`src/core/services/dfg_builder_service.py`)
- COBOL-specific tool handlers with complex parameter schemas

**Documentation**: See `docs/cobol/` for implementation details, phase plans, and progress tracking

**Running COBOL server**:
```bash
# Ensure COBOL tools are seeded in database with domain="cobol_analysis"
uv run python -m src.mcp_servers.mcp_cobol_analysis
```

This domain showcases how to build domain-specific servers with complex business logic while maintaining the shared infrastructure pattern.

## Tool Model Fields

Database schema for tools (`src/core/models/tool_model.py:13-34`):
- `name`: Unique identifier for MCP tool registration
- `description`: Shown to AI agents/users
- `handler_name`: Key to lookup function in `TOOL_HANDLERS` registry
- `category`: Functional grouping (utility, calculation, system)
- `domain`: Business domain (general, os_commands, kubernetes, shopping)
- `is_active`: Enable/disable without code changes
- `parameters_schema`: JSON Schema defining tool parameters (stored but not yet used by dynamic loader)

## Essential Commands

### Package Management
```bash
uv sync                    # Install all dependencies
uv add <package>           # Add production dependency
uv add --dev <package>     # Add dev dependency
uv remove <package>        # Remove dependency
```
**Critical**: Only use `uv` - never pip, pip-tools, or poetry.

### Database Setup
```bash
# Create database (first time only)
createdb mcp_server

# Initialize tables
uv run python scripts/init_db.py

# Load initial tools
uv run python scripts/seed_tools.py
```

Database must be initialized before starting any MCP server.

### Database Management (Helper Script)
```bash
./scripts/db.sh tools           # List all tools
./scripts/db.sh tools-active    # List active tools only
./scripts/db.sh schema          # Show database schema
./scripts/db.sh size            # Show database size and record counts
./scripts/db.sh reset           # Reset database (WARNING: deletes all data)
./scripts/db.sh backup          # Backup database to file
./scripts/db.sh restore [file]  # Restore from backup
./scripts/db.sh query "SELECT ..."  # Run custom SQL
./scripts/db.sh connect         # Open psql interactive shell
```

### Running Servers
```bash
# STDIO mode (Claude Desktop, Cursor)
uv run python -m src.mcp_servers.mcp_general

# HTTP streaming mode (web clients, port 8000)
uv run python -m src.mcp_servers.mcp_general.http_main

# Streamable HTTP mode (full MCP protocol, port 8002)
uv run python -m src.mcp_servers.mcp_general.streamable_http_main
```

**Implemented domains**:
- `mcp_general`: Fully functional general-purpose tools
- `mcp_cobol_analysis`: COBOL reverse engineering tools (in development)
- `mcp_kubernetes`, `mcp_os_commands`, `mcp_shopping`: Placeholders for demonstration

### Testing
```bash
uv run pytest                                      # All tests
uv run pytest --cov=src                           # With coverage
uv run pytest --cov=src --cov-report=html         # Coverage with HTML report
uv run pytest tests/core/test_tool_handlers.py    # Specific file
uv run pytest -m unit                             # Unit tests only
uv run pytest -m integration                      # Integration tests only
uv run pytest tests/path/file.py::test_function  # Single test
uv run pytest -k "test_name"                      # Tests matching pattern
uv run pytest -v                                  # Verbose output
uv run pytest -x                                  # Stop on first failure
uv run pytest -s                                  # Show print statements
uv run pytest -vxs                                # Verbose, stop on fail, show prints
```

### Code Quality
```bash
uv run pre-commit run --all-files  # All hooks
uv run ruff check .                # Lint
uv run ruff check --fix .          # Lint with auto-fix
uv run ruff format .               # Format
uv run mypy src/                   # Type check
```

### Database Migrations (Alembic)
```bash
# Generate migration from model changes
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Downgrade one version
uv run alembic downgrade -1

# Show migration history
uv run alembic history

# Show current revision
uv run alembic current
```

### Observability & Monitoring
```bash
# Access Prometheus metrics (HTTP server must be running)
curl http://localhost:8000/metrics

# View execution logs in database
./scripts/db.sh query "SELECT * FROM tool_executions ORDER BY started_at DESC LIMIT 10;"

# Check tool performance
./scripts/db.sh query "SELECT tool_name, COUNT(*) as calls, AVG(duration_ms) as avg_duration FROM tool_executions GROUP BY tool_name;"
```

## Adding a New Tool (4-Step Process)

**1. Handler function** (`src/core/services/tool_handlers_service.py`):
```python
def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Business logic for my_tool."""
    input_text = parameters.get("input", "")
    return {
        "success": True,
        "result": f"Processed: {input_text}",
    }
```

**2. Registry entry** (same file):
```python
TOOL_HANDLERS = {
    # ... existing handlers
    "my_tool_handler": my_tool_handler,
}
```

**3. Database record** (`scripts/seed_tools.py`):
```python
ToolCreate(
    name="my_tool",
    description="Does X with input text",
    handler_name="my_tool_handler",
    parameters_schema={
        "type": "object",
        "properties": {
            "input": {
                "type": "string",
                "description": "Input text to process"
            }
        },
        "required": ["input"]
    },
    category="utility",
    domain="general",
    is_active=True
)
```

**4. Wrapper function** (`src/mcp_servers/common/dynamic_loader.py`):

In the `register_tool_from_db` function, add a new `elif` case with observability tracing:
```python
elif tool.name == "my_tool":
    async def my_tool_wrapper(input: str) -> dict[str, Any]:
        """Does X with input text."""
        with trace_tool_execution(
            tool_name=tool.name,
            parameters={"input": input},
            domain=domain,
            transport=transport,
        ):
            try:
                result = handler_func({"input": input})
                return result
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {e}")
                return {"success": False, "error": str(e)}

    decorated_tool = mcp.tool(name=tool.name, description=tool.description)(my_tool_wrapper)
```

**Deploy** (after completing all 4 steps):
```bash
# Reset database with new tool
uv run python scripts/init_db.py
uv run python scripts/seed_tools.py

# Restart server to load new tool
uv run python -m src.mcp_servers.mcp_general
```

**Important**: All 4 steps are required - the tool won't work if any step is missing. The handler (step 1) contains business logic, the registry (step 2) makes it discoverable, the database record (step 3) provides metadata, and the wrapper (step 4) bridges FastMCP's explicit signatures with your handler.

## Creating a New Domain Server (14 Lines of Code)

To add a new domain-specific server (e.g., for Kubernetes):

**1. Create directory**:
```bash
mkdir -p src/mcp_servers/mcp_kubernetes
touch src/mcp_servers/mcp_kubernetes/__init__.py
```

**2. Create `__main__.py`**:
```python
"""Entry point for Kubernetes MCP server in STDIO mode."""
from src.mcp_servers.common.stdio_runner import run_stdio_server

if __name__ == "__main__":
    run_stdio_server(domain="kubernetes")
```

**3. Create `http_main.py`**:
```python
"""Entry point for Kubernetes MCP server in HTTP streaming mode."""
from src.mcp_servers.common.http_runner import run_http_server

if __name__ == "__main__":
    run_http_server(domain="kubernetes")
```

**4. Add tools with `domain="kubernetes"`** in `scripts/seed_tools.py` and create corresponding handlers.

**Done!** The server will automatically load tools with `domain="kubernetes"` from the database.

## Code Patterns

### Database Sessions
```python
from src.core.database import get_db

async def my_function():
    async with get_db() as db:
        tool_repo = ToolRepository(db)
        tools = await tool_repo.list_active()
```

### Configuration
```python
from src.core.config import get_settings
settings = get_settings()  # Access: settings.database_url, settings.app_name

# Observability settings
settings.enable_metrics              # Enable/disable Prometheus metrics
settings.enable_execution_logging    # Enable/disable DB logging
settings.log_tool_inputs             # Store input parameters (PII concern)
settings.log_tool_outputs            # Store output data (PII concern)
settings.metrics_retention_days      # How long to keep execution records
```

### Observability & Metrics
Tools are automatically traced with Prometheus and database logging:

```python
# Metrics are recorded automatically for all tools
# Access Prometheus metrics at: http://localhost:8000/metrics

# Query execution history from database
from src.core.repositories.tool_execution_repository import ToolExecutionRepository

async with get_db() as db:
    repo = ToolExecutionRepository(db)
    executions = await repo.get_recent_by_tool("echo", limit=10)
    stats = await repo.get_tool_stats("echo", start_time, end_time)
```

**Prometheus metrics available**:
- `mcp_tool_calls_total` - Total calls by tool, status, domain, transport
- `mcp_tool_errors_total` - Errors by type
- `mcp_tool_duration_seconds` - Latency histogram (p50, p95, p99)
- `mcp_tool_in_progress` - Current in-flight requests

**Database tracking**:
- Individual execution records with full context
- E2E tracing with correlation IDs
- Error analysis and debugging
- Audit trail for compliance

### Error Handling
Custom exceptions in `src/core/exceptions.py` are used for business logic. Interface layers (MCP/REST) translate them to protocol-specific errors. Use early returns and guard clauses.

## Development Status

**Phase 1: Tools**
- ✅ 1.1: STDIO transport (dynamic DB loading)
- ✅ 1.2: HTTP streaming transport
- ✅ 1.3: Observability & Metrics (Prometheus + Database)
- ⏳ 1.4: REST API (planned)

**Phase 2: Resources** (future)
**Phase 3: Prompts** (future)

### Observability Implementation
- ✅ **Database foundation**: `tool_executions` table with indexes
- ✅ **Prometheus metrics**: Counters, histograms, gauges
- ✅ **Automatic tracing**: All tools wrapped with `trace_tool_execution()`
- ✅ **E2E tracing**: Correlation IDs and session tracking
- ✅ **Metrics endpoint**: `/metrics` for Prometheus scraping
- ⏳ **Error pattern detection**: (planned)
- ⏳ **Grafana dashboards**: (planned)

## Code Style

Based on `.cursor/rules/python.mdc`:

**Key Principles**
- Functional over classes (except models/schemas/repos)
- Type hints mandatory on all function signatures
- Async/await for all I/O operations
- Early returns (guard clauses) for error conditions
- Descriptive names with auxiliary verbs (`is_active`, `has_permission`)
- File naming: `snake_case.py`
- Use lowercase with underscores for directories and files

**Error Handling**
- Handle errors at the beginning of functions
- Use early returns to avoid deeply nested if statements
- Place happy path last in the function
- Avoid unnecessary else statements; use if-return pattern
- Use guard clauses for preconditions and invalid states

**FastAPI-Specific**
- Use `def` for synchronous operations, `async def` for asynchronous
- Minimize blocking I/O; use async for all database and external API calls
- Use Pydantic models for input validation and response schemas
- Use dependency injection for shared resources

## Testing

- **Unit tests** (`@pytest.mark.unit`): Test `src/core/` business logic in isolation
- **Integration tests** (`@pytest.mark.integration`): Test MCP tools and REST endpoints
- Tests use in-memory SQLite (not PostgreSQL) for speed
- Fixtures: `test_engine`, `test_session`, `sample_tool_data` (see `tests/conftest.py`)

## Critical Constraints

1. **Never duplicate business logic** - keep it in `src/core/`
2. **Never duplicate server code** - use `common/` infrastructure for all domain servers
3. **UV only** - never pip, pip-tools, or poetry
4. **Type hints mandatory** - strict mypy enforced
5. **4 pieces per tool**: handler function, registry entry, DB record, wrapper function

## Debugging Tools

Tool not working? Check in order:
1. Handler in `tool_handlers_service.py` + registered in `TOOL_HANDLERS`
2. Wrapper function added to `register_tool_from_db()` in `dynamic_loader.py`
3. Tool record exists in DB with `is_active=True` and correct `domain`
4. DB was initialized before startup (log: "Loading N tools for domain...")
5. Check stderr logs (all logging goes there for Claude Desktop)
6. Verify handler accepts `parameters: dict[str, Any]` and returns `dict[str, Any]`

Use `./scripts/db.sh tools` to verify tool is in database.

## Technology Stack

- **Python 3.12+**, **UV** (package mgr), **PostgreSQL 14+**
- **FastMCP 2.0** (STDIO + HTTP streaming), **FastAPI** (REST - planned)
- **SQLAlchemy 2.0** + **asyncpg** (async Postgres)
- **Pydantic v2** (validation), **pytest** (testing)
- **Ruff** (lint/format), **mypy** (types)

## Common Development Tasks

### Adding a New Domain Server
See "Creating a New Domain Server (14 Lines of Code)" section above.

### Debugging Tool Registration
If a tool isn't appearing:
1. Verify tool exists in database: `./scripts/db.sh tools | grep tool_name`
2. Check `is_active=True` and correct `domain` value
3. Ensure handler registered in `TOOL_HANDLERS` dict
4. Verify wrapper function exists in `dynamic_loader.py`
5. Check server startup logs for "Loading N tools for domain..."
6. Restart server after database/code changes

### Working with Complex Tool Parameters
For tools requiring complex parameter validation:
1. Define comprehensive `parameters_schema` in database record
2. Use Pydantic models in `src/core/schemas/` for validation
3. Convert and validate parameters in wrapper function before passing to handler
4. See COBOL analysis tools for examples of complex schemas

### Testing Transport-Specific Behavior
```bash
# Test STDIO transport (Claude Desktop simulation)
uv run pytest tests/mcp_server/test_stdio.py -v

# Test HTTP streaming transport
uv run pytest tests/mcp_server/test_http_streaming.py -v

# Test specific tool across all transports
uv run pytest -k "test_echo_tool" -v
```

## Key Documentation

- `README.md` - Quick start and overview
- `docs/ARCHITECTURE.md` - Hexagonal architecture details
- `docs/HTTP_STREAMING.md` - HTTP streaming guide with SSE protocol comparison, pros/cons vs WebSockets/Long Polling, and MCP Inspector testing
- `docs/STREAMABLE_HTTP.md` - Streamable HTTP transport guide
- `docs/TESTING_QUICKSTART.md` - Minimal steps to test all transport types
- `docs/TESTING_GUIDE.md` - Claude Desktop integration testing
- `docs/DATABASE.md` - Database schema and management
- `docs/cobol/` - COBOL reverse engineering implementation (advanced example)

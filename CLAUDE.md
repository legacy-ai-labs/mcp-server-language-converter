# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A hybrid MCP server implementing **Hexagonal Architecture** - business logic in `src/core/` is transport-agnostic and shared by all interfaces:
- **MCP STDIO** (Claude Desktop, Cursor IDE)
- **MCP HTTP Streaming** (web-based AI clients)
- **REST API** (planned)

Part of a larger reverse engineering platform. Currently focused on COBOL analysis with extensible architecture for other languages.

## Essential Commands

```bash
# Package management (UV only - never pip/poetry)
uv sync                    # Install dependencies
uv add <package>           # Add dependency
uv add --dev <package>     # Add dev dependency

# Database
createdb mcp_server                    # Create database (first time)
uv run python scripts/init_db.py      # Initialize tables
./scripts/db.sh schema|size|reset|query "SQL"  # DB helper

# Run servers
uv run python -m src.mcp_servers.mcp_general           # STDIO (port 8000)
uv run python -m src.mcp_servers.mcp_general.http_main # HTTP streaming
uv run python -m src.mcp_servers.mcp_cobol_analysis    # COBOL STDIO
uv run python -m src.mcp_servers.mcp_cobol_analysis.http_main  # COBOL HTTP (port 8003)

# Testing
uv run pytest                              # All tests
uv run pytest tests/path/file.py::test_fn # Single test
uv run pytest -k "pattern" -vxs           # Pattern match, verbose, stop on fail
uv run pytest --cov=src --cov-report=html # Coverage

# Code quality
uv run pre-commit run --all-files  # All hooks
uv run ruff check . --fix          # Lint with auto-fix
uv run ruff format .               # Format
uv run mypy src/                   # Type check

# Database migrations
uv run alembic revision --autogenerate -m "Description"
uv run alembic upgrade head
```

## Architecture

### Directory Structure
```
src/
├── core/                    # Business logic (transport-agnostic)
│   ├── services/
│   │   ├── general/        # General tools (echo, calculator)
│   │   ├── cobol_analysis/ # COBOL reverse engineering
│   │   └── common/         # Shared utilities, observability
│   ├── models/             # SQLAlchemy models
│   ├── repositories/       # Data access layer
│   └── schemas/            # Pydantic validation
│
├── mcp_servers/
│   ├── common/             # Shared MCP infrastructure
│   │   ├── base_server.py, tool_registry.py
│   │   ├── stdio_runner.py, http_runner.py
│   │   └── observability_middleware.py
│   ├── mcp_general/        # General domain (7 lines per file)
│   └── mcp_cobol_analysis/ # COBOL domain
│
└── config/tools.json       # Tool configuration (enable/disable)
```

### Adding a New Tool (3 Steps)

**1. Handler** (`src/core/services/{domain}/tool_handlers_service.py`):
```python
def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "result": parameters.get("input")}

TOOL_HANDLERS = {"my_tool_handler": my_tool_handler}
```

**2. Decorator** (`src/mcp_servers/mcp_{domain}/tools.py`):
```python
@register_tool(domain="general", tool_name="my_tool", description="Does X")
@mcp.tool()
async def my_tool(input: str) -> dict[str, Any]:
    return my_tool_handler({"input": input})
```

**3. Config** (`config/tools.json`):
```json
{"name": "my_tool", "handler_name": "my_tool_handler", "category": "utility", "is_active": true}
```

### Creating a New Domain Server (14 Lines)

```bash
mkdir -p src/mcp_servers/mcp_newdomain
```

`__main__.py`:
```python
from src.mcp_servers.common.stdio_runner import run_stdio_server
if __name__ == "__main__":
    run_stdio_server(domain="newdomain")
```

`http_main.py`:
```python
from src.mcp_servers.common.http_runner import run_http_server
if __name__ == "__main__":
    run_http_server(domain="newdomain")
```

## COBOL Analysis Domain

Services in `src/core/services/cobol_analysis/`:
- `asg_builder_service.py` - Abstract Semantic Graph with symbol tables, cross-references
- `cobol_preprocessor_service.py` - COPY/REPLACE statement handling, copybook resolution
- `cobol_parser_antlr_service.py` - ANTLR-based parsing
- `tool_handlers_service.py` - COBOL tool handlers

Key tools:
- `parse_cobol` - Parse COBOL source to AST
- `build_asg` - Build Abstract Semantic Graph with semantic analysis
- `analyze_complexity` - Complexity metrics with optional `build_asg`, `build_cfg`, `build_dfg`, `auto_enhance` parameters
- `resolve_copybooks` - Resolve COPY statements
- `batch_analyze_cobol_directory` - Analyze entire directory of COBOL programs
- `analyze_program_system` - Inter-program relationship analysis
- `build_call_graph` - Generate program call graph

Models in `src/core/models/`:
- `complexity_metrics_model.py` - ComplexityMetrics with ASGMetrics, CFGMetrics, DFGMetrics for progressive analysis

## Code Patterns

```python
# Database sessions
from src.core.database import get_db
async with get_db() as db:
    repo = ToolRepository(db)

# Configuration
from src.core.config import get_settings
settings = get_settings()  # settings.database_url, settings.enable_metrics
```

**Observability**: All tools automatically traced with Prometheus metrics and database logging. Access at `http://localhost:8000/metrics`.

## Code Style

- Functional over classes (except models/schemas/repos)
- Type hints mandatory, strict mypy
- Async/await for all I/O
- Early returns (guard clauses) for errors
- File naming: `snake_case.py`

## Debugging Tools

If a tool isn't working, check in order:
1. Handler in `tool_handlers_service.py` + registered in `TOOL_HANDLERS`
2. Decorator in domain `tools.py`
3. Entry in `config/tools.json` with `is_active: true`
4. Server startup logs for "Loading N tools for domain..."

## Technology Stack

Python 3.12+, UV, PostgreSQL 14+, FastMCP 2.0, FastAPI, SQLAlchemy 2.0 + asyncpg, Pydantic v2, pytest, Ruff, mypy

## Key Documentation

- `docs/ARCHITECTURE.md` - Hexagonal architecture details
- `docs/HTTP_STREAMING.md` - HTTP streaming guide
- `docs/TESTING_QUICKSTART.md` - Test all transport types
- `docs/LANGGRAPH_ARCHITECTURE.md` - Multi-agent LangGraph workflow for COBOL reverse engineering
- `docs/cobol/` - COBOL implementation details

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

# Run servers (unified runner - preferred)
uv run python -m src.mcp_servers.mcp_general stdio            # STDIO transport
uv run python -m src.mcp_servers.mcp_general sse              # SSE General: http://<IP>:8000/sse
uv run python -m src.mcp_servers.mcp_general streamable-http  # Streamable HTTP General: http://<IP>:8002/mcp
uv run python -m src.mcp_servers.mcp_cobol_analysis stdio     # COBOL STDIO
uv run python -m src.mcp_servers.mcp_cobol_analysis sse       # SSE COBOL: http://<IP>:8001/sse
uv run python -m src.mcp_servers.mcp_cobol_analysis streamable-http  # Streamable HTTP COBOL: http://<IP>:8003/mcp

# ProLeap COBOL Parser (Java-based, for validation)
uv run python scripts/proleap_ast_export.py <cobol_file>  # Export AST to JSON
uv run python scripts/proleap_asg_export.py <cobol_file>  # Export ASG to JSON

# Testing
uv run pytest                              # All tests
uv run pytest tests/path/file.py::test_fn # Single test
uv run pytest -k "pattern" -vxs           # Pattern match, verbose, stop on fail
uv run pytest -m "not slow"               # Skip slow tests
uv run pytest -m integration              # Only integration tests
uv run pytest --cov=src --cov-report=html # Coverage

# Code quality
uv run pre-commit run --all-files  # All hooks
uv run ruff check . --fix          # Lint with auto-fix
uv run ruff format .               # Format
uv run mypy src/                   # Type check

# Database migrations
uv run alembic revision --autogenerate -m "Description"
uv run alembic upgrade head

# Docker (for containerized deployment)
docker compose -f docker/docker-compose.yml up -d      # Start all services
docker compose -f docker/docker-compose.yml logs -f    # View logs
docker compose -f docker/docker-compose.yml down       # Stop services
docker compose -f docker/docker-compose.yml up -d --build  # Rebuild and restart

# MCP Inspector (debugging tool)
npx @modelcontextprotocol/inspector  # Opens http://localhost:3000

# Kill running MCP processes (macOS)
lsof -ti:8000,8001,8002,8003,9090 | xargs -r kill   # Kill by port
pkill -f "src.mcp_servers.mcp_general" || true  # Kill by module
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
│   │   ├── base_server.py              # FastMCP initialization
│   │   ├── unified_runner.py           # Protocol-agnostic runner (stdio/sse/streamable-http)
│   │   ├── tool_registry.py            # Decorator-based tool registration
│   │   └── observability_middleware.py # Metrics and tracing
│   ├── mcp_general/        # General domain
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

### Creating a New Domain Server

```bash
mkdir -p src/mcp_servers/mcp_newdomain
```

`__main__.py`:
```python
"""Entry point for NewDomain MCP server."""
import sys
from src.mcp_servers.common.unified_runner import run_server

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    run_server(domain="newdomain", transport=transport)
```

Usage:
```bash
uv run python -m src.mcp_servers.mcp_newdomain stdio
uv run python -m src.mcp_servers.mcp_newdomain sse
uv run python -m src.mcp_servers.mcp_newdomain streamable-http
```

## COBOL Analysis Domain

Services in `src/core/services/cobol_analysis/`:
- `asg_builder_service.py` - Abstract Semantic Graph with symbol tables, cross-references
- `cfg_builder_service.py` - Control Flow Graph with cyclomatic complexity, unreachable code detection
- `dfg_builder_service.py` - Data Flow Graph with dead variable/uninitialized read detection
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

**Observability**: All tools automatically traced with Prometheus metrics and database logging. Access at `http://localhost:9090/metrics` (health: `http://localhost:9090/health`).

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

## Docker Ports (Quick Reference)

| Port | Description | Endpoint |
|------|-------------|----------|
| 8000 | SSE General | `http://<IP>:8000/sse` |
| 8001 | SSE COBOL | `http://<IP>:8001/sse` |
| 8002 | Streamable HTTP General | `http://<IP>:8002/mcp` |
| 8003 | Streamable HTTP COBOL | `http://<IP>:8003/mcp` |
| 9090 | Health Check | `http://<IP>:9090/health` |
| 9090 | Prometheus Metrics | `http://<IP>:9090/metrics` |

## Key Documentation

- `docs/ARCHITECTURE.md` - Hexagonal architecture details
- `docs/DOCKER.md` - Docker deployment guide (Dockerfile, docker-compose, supervisord)
- `docs/HTTP_STREAMING.md` - HTTP streaming guide
- `docs/STREAMABLE_HTTP.md` - Streamable HTTP transport guide
- `docs/TESTING_QUICKSTART.md` - Test all transport types (unified runner, MCP Inspector)
- `docs/LANGGRAPH_ARCHITECTURE.md` - Multi-agent LangGraph workflow for COBOL reverse engineering
- `docs/cobol/` - COBOL implementation details

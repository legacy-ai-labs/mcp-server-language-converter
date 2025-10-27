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
│   ├── dynamic_loader.py       # Generic DB tool loading
│   ├── stdio_runner.py         # Generic STDIO transport
│   └── http_runner.py          # Generic HTTP streaming transport
│
├── mcp_general/                # Domain-specific servers (minimal code)
│   ├── __main__.py             # 7 lines: run_stdio_server(domain="general")
│   └── http_main.py            # 7 lines: run_http_server(domain="general")
│
├── mcp_kubernetes/             # Future: Same pattern
│   ├── __main__.py             # 7 lines: run_stdio_server(domain="kubernetes")
│   └── http_main.py            # 7 lines: run_http_server(domain="kubernetes")
└── ...
```

**Key benefit**: Adding a new domain server requires only **14 lines of code** (2 files × 7 lines each).

### Dynamic Tool Loading System

Tools are **database-driven** with a 3-part registration flow (simplified from 4):

1. **Handler Function** (`src/core/services/tool_handlers.py`): Pure business logic
   ```python
   def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
       return {"success": True, "result": parameters.get("input")}
   ```

2. **Handler Registry** (`TOOL_HANDLERS` dict in same file): Maps names to functions
   ```python
   TOOL_HANDLERS = {"my_tool_handler": my_tool_handler}
   ```

3. **Database Record** (`Tool` model): Metadata (name, description, domain, category, active status)

**No per-tool wrapper code needed!** The generic loader in `common/dynamic_loader.py` automatically creates wrappers using `**kwargs`.

**Startup sequence**: Tools loaded from DB **before** `mcp.run()` - handled automatically by runners in `common/`.

### Multi-Server Architecture

This blueprint supports **multiple domain-specific servers** (general, kubernetes, os_commands, shopping). Each loads tools filtered by `domain` field from the database. This pattern is useful for:
- **Security boundaries** (different permission levels)
- **Independent scaling** (scale high-traffic domains separately)
- **Team ownership** (different teams own different domains)

**Note**: Most real-world MCP servers use a single server with many tools. Use multiple servers only when you need the benefits above.

## Tool Model Fields

Database schema for tools (`src/core/models/tool.py:13-34`):
- `name`: Unique identifier for MCP tool registration
- `description`: Shown to AI agents/users
- `handler_name`: Key to lookup function in `TOOL_HANDLERS` registry
- `category`: Functional grouping (utility, calculation, system)
- `domain`: Business domain (general, os_commands, kubernetes, shopping)
- `is_active`: Enable/disable without code changes
- `parameters_schema`: Reserved for future use (currently unused)

## Essential Commands

### Package Management
```bash
uv sync                    # Install all dependencies
uv add <package>           # Add dependency
uv add --dev <package>     # Add dev dependency
uv remove <package>        # Remove dependency
```
**Critical**: Only use `uv` - never pip, pip-tools, or poetry.

### Database Setup
```bash
uv run python scripts/init_db.py    # Create tables
uv run python scripts/seed_tools.py # Load initial tools
```
Database must be initialized before starting any MCP server.

### Running Servers
```bash
# STDIO mode (Claude Desktop, Cursor)
uv run python -m src.mcp_servers.mcp_general

# HTTP streaming mode (web clients)
uv run python -m src.mcp_servers.mcp_general.http_main  # Port 8000
```

**Note**: The directory structure shows `mcp_general/`, `mcp_kubernetes/`, `mcp_os_commands/`, `mcp_shopping/`. These demonstrate multi-server patterns but only `mcp_general` is implemented. The others are placeholders.

### Testing
```bash
uv run pytest                                      # All tests
uv run pytest --cov=src                           # With coverage
uv run pytest tests/core/test_tool_handlers.py    # Specific file
uv run pytest -m unit                             # Unit tests only
uv run pytest -m integration                      # Integration tests only
uv run pytest tests/path/file.py::test_function  # Single test
```

### Code Quality
```bash
uv run pre-commit run --all-files  # All hooks
uv run ruff check .                # Lint
uv run ruff format .               # Format
uv run mypy src/                   # Type check
```

## Adding a New Tool (3-Step Process)

**1. Handler function** (`src/core/services/tool_handlers.py`):
```python
def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Business logic for my_tool."""
    return {"success": True, "result": parameters.get("input")}
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
Tool(name="my_tool", description="Does X", handler_name="my_tool_handler",
     category="utility", domain="general", is_active=True)
```

Then run: `uv run python scripts/init_db.py && uv run python scripts/seed_tools.py`

**That's it!** No wrapper code needed - the generic loader in `common/dynamic_loader.py` handles it automatically.

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
```

### Error Handling
Custom exceptions in `src/core/exceptions.py` are used for business logic. Interface layers (MCP/REST) translate them to protocol-specific errors.

## Development Status

**Phase 1: Tools**
- ✅ 1.1: STDIO transport (dynamic DB loading)
- ✅ 1.2: HTTP streaming transport
- ⏳ 1.3: REST API (planned)

**Phase 2: Resources** (future)
**Phase 3: Prompts** (future)

## Code Style (from .cursor/rules)

- Functional over classes (except models/schemas/repos)
- Type hints mandatory on all function signatures
- Async/await for all I/O operations
- Early returns (guard clauses) for error conditions
- Descriptive names with auxiliary verbs (`is_active`, `has_permission`)
- File naming: `snake_case.py`

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
5. **3 pieces per tool**: handler function, registry entry, DB record (no wrapper code needed!)

## Debugging Tools

Tool not working? Check in order:
1. Handler in `tool_handlers.py` + registered in `TOOL_HANDLERS`
2. Tool record exists in DB with `is_active=True` and correct `domain`
3. DB was initialized before startup (log: "Tools loaded successfully")
4. Check stderr logs (all logging goes there for Claude Desktop)
5. Verify handler accepts `parameters: dict[str, Any]` and returns `dict[str, Any]`

No need to check wrapper code - it's generic now!

## Technology Stack

- **Python 3.12+**, **UV** (package mgr), **PostgreSQL 14+**
- **FastMCP 2.0** (STDIO + HTTP streaming), **FastAPI** (REST - planned)
- **SQLAlchemy 2.0** + **asyncpg** (async Postgres)
- **Pydantic v2** (validation), **pytest** (testing)
- **Ruff** (lint/format), **mypy** (types)

## Key Documentation

- `README.md` - Quick start and overview
- `docs/ARCHITECTURE.md` - Hexagonal architecture details
- `docs/HTTP_STREAMING.md` - HTTP streaming guide with MCP Inspector
- `TESTING_GUIDE.md` - Claude Desktop integration testing
- `docs/DATABASE.md` - Database schema and management

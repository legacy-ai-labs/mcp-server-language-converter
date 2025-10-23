# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A hybrid MCP (Model Context Protocol) server implementation that supports **multiple domain-specific MCP servers**, each exposing the same business logic through multiple interfaces:
- **MCP protocol** (STDIO and HTTP streaming) via FastMCP 2.0
- **REST API** via FastAPI

The core principle: implement business logic once, expose it everywhere.

## Architecture

The project follows **Hexagonal/Ports and Adapters** architecture with **domain-specific MCP servers**:

```
src/
├── core/                    # Transport-agnostic business logic (single source of truth)
│   ├── models/             # Database models (SQLAlchemy)
│   ├── repositories/       # Data access layer
│   ├── schemas/            # Pydantic validation schemas
│   ├── services/           # Business logic and tool handlers
│   ├── config.py           # Application settings (Pydantic settings)
│   ├── database.py         # Database engine and session management
│   └── exceptions.py       # Custom exceptions
├── mcp_servers/            # Domain-specific MCP servers
│   ├── general/            # General purpose tools (echo, calculator)
│   │   ├── server.py       # MCP server initialization
│   │   ├── tools.py        # MCP tool definitions
│   │   ├── dependencies.py # MCP-specific dependencies
│   │   └── __main__.py     # Entry point for STDIO mode
│   ├── os_commands/        # OS-specific tools (future)
│   ├── kubernetes/         # K8s-specific tools (future)
│   └── shopping/           # E-commerce tools (future)
└── rest_api/               # Shared REST API
    └── routes/             # REST endpoint definitions
```

**Critical rules**:
1. Business logic lives in `src/core/` and is shared by all MCP servers and REST API
2. Each domain-specific MCP server in `src/mcp_servers/` handles one domain
3. Never duplicate business logic between interfaces or servers

## Development Commands

### Package Management (UV only)
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>

# Remove dependency
uv remove <package-name>

# Run script with UV
uv run python script.py
```

**Never use pip, pip-tools, or poetry**. UV is the exclusive package manager.

### Database Operations
```bash
# Initialize database and create tables
uv run python scripts/init_db.py

# Seed initial tools
uv run python scripts/seed_tools.py
```

Database URL configured in `.env`:
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mcp_server
```

### Running MCP Servers
```bash
# Run the General MCP server (STDIO mode, for Claude Desktop/Cursor)
uv run python -m src.mcp_servers.general

# Future: Run other domain-specific servers
# uv run python -m src.mcp_servers.os_commands
# uv run python -m src.mcp_servers.kubernetes
# uv run python -m src.mcp_servers.shopping
```

**Note**:
- Tools are statically registered via `@mcp.tool()` decorators
- No database initialization needed for basic tool functionality
- Dynamic tool loading from the database is planned for a future phase

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/core/test_tool_handlers.py

# Run specific test
uv run pytest tests/core/test_tool_handlers.py::test_echo_handler

# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration
```

### Code Quality
```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# Lint with Ruff
uv run ruff check .

# Format with Ruff
uv run ruff format .

# Type check with mypy
uv run mypy src/
```

## Key Development Patterns

### 1. Adding a New MCP Tool to a Domain-Specific Server

Tools are registered using FastMCP decorators in the appropriate domain server's `tools.py` file (e.g., `src/mcp_servers/general/tools.py`).

**Step 1**: Create the handler function in `src/core/services/tool_handlers.py`:
```python
def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Handler for my custom tool.

    This is the core business logic that can be reused by both MCP and REST interfaces.
    """
    # Business logic here
    return {"success": True, "result": "..."}
```

**Step 2**: Add the MCP tool decorator in the domain server's `tools.py` (e.g., `src/mcp_servers/general/tools.py`):
```python
from src.mcp_servers.general.server import mcp
from src.core.services.tool_handlers import my_tool_handler

@mcp.tool(name="my_tool", description="Description of the tool")
async def my_tool(param1: str) -> dict[str, Any]:
    """MCP tool wrapper that calls the core business logic."""
    try:
        result = my_tool_handler({"param1": param1})
        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return {"success": False, "error": str(e)}
```

**Step 3**: Import the tools module in `__main__.py` to ensure decorators are registered:
```python
import src.mcp_servers.general.tools  # noqa: F401
```

The tool will automatically be available when the MCP server starts.

### 2. Creating a New Domain-Specific MCP Server

To create a new domain-specific MCP server (e.g., for Kubernetes tools):

**Step 1**: Create the server directory structure:
```bash
mkdir -p src/mcp_servers/kubernetes
touch src/mcp_servers/kubernetes/__init__.py
touch src/mcp_servers/kubernetes/server.py
touch src/mcp_servers/kubernetes/tools.py
touch src/mcp_servers/kubernetes/__main__.py
```

**Step 2**: Initialize the MCP server in `server.py`:
```python
from fastmcp import FastMCP
from src.core.config import get_settings

settings = get_settings()

mcp = FastMCP(
    name=f"{settings.app_name} - Kubernetes Tools",
    version=settings.app_version,
)
```

**Step 3**: Add tools in `tools.py`:
```python
from src.mcp_servers.kubernetes.server import mcp
from src.core.services.tool_handlers import k8s_handler

@mcp.tool(name="k8s_tool", description="K8s tool")
async def k8s_tool(param: str) -> dict[str, Any]:
    # Implementation
    pass
```

**Step 4**: Create entry point in `__main__.py` (follow pattern in `src/mcp_servers/general/__main__.py`)

**Critical**: The `@mcp.tool()` decorator must be applied before `mcp.run()` is called. Ensure tools are imported in `__main__.py` so decorators execute during module import.

### 3. Database Session Management

Use dependency injection for database sessions:

```python
from src.core.database import get_db

async def some_function():
    async with get_db() as db:
        # Use db session here
        tool_repo = ToolRepository(db)
        tools = await tool_repo.list_active()
```

### 4. Configuration Management

Settings are loaded from `.env` via Pydantic:

```python
from src.core.config import get_settings

settings = get_settings()
# Access: settings.database_url, settings.app_name, etc.
```

### 5. Error Handling

Use custom exceptions from `src/core/exceptions.py` for business logic errors. Interface layers (MCP/REST) translate these to appropriate protocol errors.

## Multi-Server Architecture Benefits

The domain-specific server approach provides:

1. **Separation of Concerns**: Each server handles one domain (general, OS, K8s, shopping)
2. **Shared Infrastructure**: All servers use the same database, repositories, and services
3. **Independent Scaling**: Each server can be scaled separately
4. **Security**: Domain-specific permissions and isolation
5. **Maintainability**: Easier to debug and update specific domains

When adding new functionality, always place business logic in `src/core/` and create domain-specific wrappers in the appropriate `src/mcp_servers/[domain]/` directory.

## Development Phases

The project follows a phased development approach:

**Phase 1: Tools** (Current)
- 1.1: Tools via STDIO (✅ Completed)
- 1.2: Tools via HTTP Streaming (Planned)
- 1.3: Tools via REST API (Planned)

**Phase 2: Resources** (Future)
- 2.1-2.3: Resources across all transports

**Phase 3: Prompts** (Future)
- 3.1-3.3: Prompts across all transports

## Code Style Guidelines

From `.cursor/python.mdc`:
- Use functional, declarative programming; avoid classes where possible (except for models, schemas, repos)
- Type hints required for all function signatures
- Use Pydantic models for validation
- Prefer async/await for I/O operations
- Early returns for error conditions (guard clauses)
- Use descriptive variable names with auxiliary verbs (e.g., `is_active`, `has_permission`)
- File naming: lowercase with underscores (e.g., `tool_repository.py`)

## Testing Strategy

- **Unit tests**: Test business logic in `src/core/` in isolation
- **Integration tests**: Test MCP tools and REST endpoints
- Use pytest fixtures in `tests/conftest.py` for common setup
- Mock database calls when testing handlers
- Aim for >80% code coverage

## Important Constraints

1. **Never duplicate business logic** between MCP and REST interfaces
2. **Always use UV** for package management, never pip
3. **Database initialization must happen in lifespan events** - never before `mcp.run()`
4. **Type hints are mandatory** - strict mypy configuration is enforced
5. **Pre-commit hooks must pass** before commits
6. **Use async/await** for all I/O operations (database, external APIs)

## Common Tasks

### Adding a new Python dependency
```bash
uv add <package-name>
# This updates pyproject.toml and uv.lock automatically
```

### Debugging tool execution
Tools are executed through the handler registry. Check:
1. Handler exists in `src/core/services/tool_handlers.py`
2. Tool is registered with `@mcp.tool()` decorator in the domain server's `tools.py` (e.g., `src/mcp_servers/general/tools.py`)
3. Tools module is imported in `__main__.py` to ensure decorators are registered
4. Parameter types match between decorator and handler
5. Logs are written to stderr for Claude Desktop debugging (check `logging.basicConfig(..., stream=sys.stderr)`)

### Updating database schema
Currently using direct SQLAlchemy models. Alembic migrations will be added in the future.
For now, modify models in `src/core/models/` and recreate database:
```bash
uv run python scripts/init_db.py
```

### Testing Claude Desktop integration
See [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed instructions on setting up and testing with Claude Desktop.

## File Naming Conventions

- Python files: `snake_case.py`
- Test files: `test_*.py` matching source file names
- Directories: `snake_case/`
- Database models: Singular nouns (e.g., `Tool`, not `Tools`)
- Schemas: Match model names (e.g., `ToolCreate`, `ToolResponse`)

## Technology Stack

- **Python**: 3.12+ (use modern features)
- **UV**: Package manager and script runner
- **FastMCP 2.0**: MCP server framework (STDIO and HTTP streaming)
- **FastAPI**: REST API framework
- **SQLAlchemy 2.0**: Async ORM for PostgreSQL
- **asyncpg**: Async PostgreSQL driver
- **Pydantic v2**: Data validation and settings
- **pytest**: Testing framework
- **Ruff**: Linting and formatting
- **mypy**: Static type checking

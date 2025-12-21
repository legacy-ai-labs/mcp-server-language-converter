# Migration Plan: Database-Driven to Hybrid Decorator-Based Tool Registration

## Executive Summary

This document outlines the migration from the current database-driven dynamic tool loading approach to a hybrid approach that uses FastMCP decorators (`@mcp.tool()`) for tool registration while maintaining database metadata for management, observability, and runtime configuration.

**Migration Timeline**: Phased approach over 2-3 weeks
**Risk Level**: Medium (backward compatible during transition)
**Breaking Changes**: None (both systems will coexist during migration)

---

## Current State Analysis

### Current Architecture

**Tool Registration Flow:**
1. Tool metadata stored in database (`tools` table)
2. Handler functions in domain-specific `tool_handlers_service.py` files
3. Manual wrapper functions in `dynamic_loader.py` (one per tool)
4. Tools loaded from DB at startup via `load_tools_from_database()`

**Problems:**
- ❌ Manual wrapper function required for each tool (not scalable)
- ❌ Triple definition: DB record + handler + wrapper
- ❌ FastMCP limitation: requires explicit signatures, can't use `**kwargs`
- ❌ Maintenance burden: 4-step process to add a tool
- ❌ No type safety or IDE support for tool signatures

**Current File Structure:**
```
src/
├── core/
│   └── services/
│       ├── general/
│       │   └── tool_handlers_service.py  # echo_handler, calculator_add_handler
│       └── cobol_analysis/
│           └── tool_handlers_service.py   # parse_cobol_handler, build_ast_handler, etc.
└── mcp_servers/
    ├── common/
    │   └── dynamic_loader.py              # Manual wrappers: _create_echo_tool, etc.
    └── mcp_general/
        ├── __main__.py                     # Calls run_stdio_server()
        └── http_main.py                    # Calls run_http_server()
```

---

## Target State

### Hybrid Architecture

**Tool Registration Flow:**
1. Tools registered using `@mcp.tool()` decorators in domain-specific `tools.py` files
2. Handler functions remain in domain-specific `tool_handlers_service.py` files
3. Database stores metadata for enable/disable, observability, versioning
4. Tools loaded from decorators at startup, filtered by DB `is_active` flag

**Benefits:**
- ✅ No manual wrappers needed
- ✅ Type-safe tool signatures with IDE support
- ✅ Single source of truth for tool implementation
- ✅ Database still provides runtime control (enable/disable)
- ✅ Scalable: adding tools is just decorator + handler

**Target File Structure:**
```
src/
├── core/
│   └── services/
│       ├── general/
│       │   └── tool_handlers_service.py  # Business logic (unchanged)
│       └── cobol_analysis/
│           └── tool_handlers_service.py  # Business logic (unchanged)
└── mcp_servers/
    ├── common/
    │   ├── base_server.py                 # create_mcp_server() (unchanged)
    │   ├── stdio_runner.py                # Updated to load from decorators
    │   ├── http_runner.py                 # Updated to load from decorators
    │   └── tool_registry.py               # NEW: Decorator-based registration
    └── mcp_general/
        ├── tools.py                        # NEW: @mcp.tool() decorators
        ├── __main__.py                     # Updated to use tool_registry
        └── http_main.py                    # Updated to use tool_registry
```

---

## Migration Strategy

### Phase 1: Foundation (Week 1, Days 1-2)

**Goal**: Create new infrastructure while keeping old system working

#### Step 1.1: Create Tool Registry Module

Create `src/mcp_servers/common/tool_registry.py`:

```python
"""Tool registry for decorator-based tool registration.

This module provides a registry pattern that allows domain-specific servers
to register tools using @mcp.tool() decorators while maintaining compatibility
with database-driven enable/disable functionality.
"""

import logging
from typing import Any, Callable

from fastmcp import FastMCP

from src.core.database import async_session_factory
from src.core.repositories.tool_repository import ToolRepository

logger = logging.getLogger(__name__)

# Global registry: domain -> list of (tool_name, tool_func, description)
TOOL_REGISTRY: dict[str, list[tuple[str, Callable[..., Any], str]]] = {}


def register_tool(domain: str, tool_name: str, description: str = ""):
    """Decorator factory for registering tools in the registry.

    Usage:
        @register_tool(domain="general", tool_name="echo", description="Echo text")
        @mcp.tool()
        async def echo(text: str) -> dict[str, Any]:
            ...

    Args:
        domain: Domain this tool belongs to
        tool_name: Name of the tool (must match DB record)
        description: Tool description (optional, can come from DB)

    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if domain not in TOOL_REGISTRY:
            TOOL_REGISTRY[domain] = []

        TOOL_REGISTRY[domain].append((tool_name, func, description))
        logger.debug(f"Registered tool '{tool_name}' for domain '{domain}'")
        return func

    return decorator


async def load_tools_from_registry(
    mcp: FastMCP,
    domain: str,
    transport: str = "stdio",
) -> None:
    """Load tools from registry and register with FastMCP, filtered by database.

    This function:
    1. Gets all registered tools for the domain from TOOL_REGISTRY
    2. Checks database to see which tools are active
    3. Registers only active tools with FastMCP
    4. Applies observability tracing to all tools

    Args:
        mcp: FastMCP server instance
        domain: Domain to load tools for
        transport: Transport protocol (stdio, http, sse)

    Raises:
        Exception: If tool loading fails
    """
    if domain not in TOOL_REGISTRY:
        logger.warning(f"No tools registered for domain '{domain}'")
        return

    try:
        async with async_session_factory() as session:
            tool_repo = ToolRepository(session)

            # Get active tools from database for this domain
            active_tools = await tool_repo.get_by_domain(domain)
            active_tool_names = {tool.name for tool in active_tools}

            # Get registered tools for this domain
            registered_tools = TOOL_REGISTRY.get(domain, [])

            logger.info(
                f"Loading {len(registered_tools)} registered tools for domain '{domain}' "
                f"({len(active_tool_names)} active in database)"
            )

            # Register each tool that is both registered and active in DB
            registered_count = 0
            for tool_name, tool_func, description in registered_tools:
                if tool_name not in active_tool_names:
                    logger.debug(f"Skipping tool '{tool_name}' (not active in database)")
                    continue

                # Find DB record for description/metadata
                db_tool = next((t for t in active_tools if t.name == tool_name), None)
                final_description = db_tool.description if db_tool else description

                # Apply observability wrapper
                traced_tool = _wrap_with_observability(
                    tool_func,
                    tool_name,
                    domain,
                    transport,
                )

                # Register with FastMCP
                mcp.tool(name=tool_name, description=final_description)(traced_tool)
                registered_count += 1
                logger.info(f"Registered tool: {tool_name}")

            logger.info(f"Successfully registered {registered_count} tools for domain '{domain}'")

            # Warn about tools in DB but not registered
            db_tool_names = {tool.name for tool in active_tools}
            registered_tool_names = {name for name, _, _ in registered_tools}
            missing_tools = db_tool_names - registered_tool_names
            if missing_tools:
                logger.warning(
                    f"Tools in database but not registered in code: {missing_tools}. "
                    f"These will not be available."
                )

    except Exception as e:
        logger.error(f"Failed to load tools from registry: {e}")
        raise


def _wrap_with_observability(
    tool_func: Callable[..., Any],
    tool_name: str,
    domain: str,
    transport: str,
) -> Callable[..., Any]:
    """Wrap tool function with observability tracing.

    Args:
        tool_func: Original tool function
        tool_name: Name of the tool
        domain: Domain the tool belongs to
        transport: Transport protocol

    Returns:
        Wrapped function with observability
    """
    from src.core.services.common.observability_service import trace_tool_execution

    async def traced_tool(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Tool wrapper with observability."""
        # Build parameters dict for tracing
        parameters = kwargs.copy() if kwargs else {}
        if args:
            # Map positional args to parameter names
            import inspect
            sig = inspect.signature(tool_func)
            param_names = list(sig.parameters.keys())
            for idx, arg in enumerate(args):
                if idx < len(param_names):
                    parameters[param_names[idx]] = arg

        async with trace_tool_execution(
            tool_name=tool_name,
            parameters=parameters,
            domain=domain,
            transport=transport,
        ) as trace_ctx:
            try:
                result = await tool_func(*args, **kwargs)
                trace_ctx["output_data"] = result
                if not isinstance(result, dict):
                    logger.warning(
                        f"Tool {tool_name} returned non-dict result: {type(result).__name__}"
                    )
                    return {
                        "success": False,
                        "error": f"Tool returned invalid type: {type(result).__name__}",
                    }
                return result
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                trace_ctx["status"] = "error"
                trace_ctx["error_type"] = type(e).__name__
                trace_ctx["error_message"] = str(e)
                return {"success": False, "error": str(e)}

    return traced_tool
```

#### Step 1.2: Create First Domain Tools File

Create `src/mcp_servers/mcp_general/tools.py`:

```python
"""Tool definitions for general domain using decorator-based registration."""

from typing import Any

from fastmcp import FastMCP
from src.core.services.common.observability_service import trace_tool_execution
from src.core.services.general.tool_handlers_service import (
    calculator_add_handler,
    echo_handler,
)
from src.mcp_servers.common.tool_registry import register_tool

# Create FastMCP instance for this domain
mcp = FastMCP("general")


@register_tool(domain="general", tool_name="echo", description="Echo back the provided text")
@mcp.tool()
async def echo(text: str) -> dict[str, Any]:
    """Echo back the provided text. Useful for testing and simple text repetition."""
    return echo_handler({"text": text})


@register_tool(
    domain="general",
    tool_name="calculator_add",
    description="Add two numbers together. Performs simple addition operation.",
)
@mcp.tool()
async def calculator_add(a: float, b: float) -> dict[str, Any]:
    """Add two numbers together. Performs simple addition operation."""
    return calculator_add_handler({"a": a, "b": b})
```

**Note**: Observability tracing will be applied automatically by `load_tools_from_registry()`, so we don't need to add it in each tool function.

#### Step 1.3: Update Runners to Support Both Systems

Modify `stdio_runner.py` and `http_runner.py` to support both old and new systems:

```python
# In stdio_runner.py, update startup() function:

async def startup(domain: str, server_name: str | None = None, use_decorators: bool = False) -> Any:
    """Initialize MCP server and load tools for the specified domain.

    Args:
        domain: Domain to load tools for
        server_name: Optional custom server name
        use_decorators: If True, use decorator-based registration; else use DB-driven

    Returns:
        Initialized FastMCP server instance
    """
    # ... existing Prometheus setup ...

    mcp = create_mcp_server(domain=domain, server_name=server_name)

    if use_decorators:
        # Import domain tools module to trigger registration
        _import_domain_tools(domain)
        # Load from registry
        from src.mcp_servers.common.tool_registry import load_tools_from_registry
        await load_tools_from_registry(mcp, domain, transport="stdio")
    else:
        # Legacy: load from database
        from src.mcp_servers.common.dynamic_loader import load_tools_from_database
        await load_tools_from_database(mcp, domain, transport="stdio")

    return mcp


def _import_domain_tools(domain: str) -> None:
    """Import domain tools module to trigger decorator registration."""
    try:
        if domain == "general":
            import src.mcp_servers.mcp_general.tools  # noqa: F401
        elif domain == "cobol_analysis":
            import src.mcp_servers.mcp_cobol_analysis.tools  # noqa: F401
        # Add more domains as they migrate
    except ImportError as e:
        logger.warning(f"Could not import tools for domain '{domain}': {e}")
```

**Testing**: Verify both systems work by running with `use_decorators=False` (old) and `use_decorators=True` (new).

---

### Phase 2: Migrate General Domain (Week 1, Days 3-4)

**Goal**: Fully migrate `general` domain to decorator-based system

#### Step 2.1: Complete General Tools File

Ensure all general domain tools are in `mcp_general/tools.py` with proper decorators.

#### Step 2.2: Update General Server Entry Points

Update `mcp_general/__main__.py` and `mcp_general/http_main.py`:

```python
# mcp_general/__main__.py
from src.mcp_servers.common.stdio_runner import run_stdio_server

if __name__ == "__main__":
    # Use decorator-based registration
    run_stdio_server(domain="general", use_decorators=True)
```

#### Step 2.3: Remove Manual Wrappers for General Tools

In `dynamic_loader.py`, remove or deprecate:
- `_create_echo_tool()`
- `_create_calculator_add_tool()`
- Related `elif` branches in `register_tool_from_db()`

**Keep**: Generic fallback for tools not yet migrated.

#### Step 2.4: Add Integration Tests

Create tests to verify decorator-based tools work:

```python
# tests/mcp_server/test_decorator_tools.py
import pytest
from fastmcp import FastMCP

from src.mcp_servers.common.tool_registry import load_tools_from_registry
from src.mcp_servers.mcp_general import tools  # Import to trigger registration


@pytest.mark.asyncio
async def test_general_tools_registered():
    """Test that general domain tools are registered via decorators."""
    mcp = FastMCP("test")
    await load_tools_from_registry(mcp, domain="general", transport="stdio")

    # Verify tools are registered
    tool_names = {tool.name for tool in mcp.list_tools()}
    assert "echo" in tool_names
    assert "calculator_add" in tool_names
```

---

### Phase 3: Migrate COBOL Analysis Domain (Week 2, Days 1-3)

**Goal**: Migrate all COBOL tools to decorator-based system

#### Step 3.1: Create COBOL Tools File

Create `src/mcp_servers/mcp_cobol_analysis/tools.py`:

```python
"""Tool definitions for COBOL analysis domain using decorator-based registration."""

from typing import Any

from fastmcp import FastMCP
from src.core.services.cobol_analysis.tool_handlers_service import (
    build_ast_handler,
    build_cfg_handler,
    build_dfg_handler,
    build_pdg_handler,
    parse_cobol_handler,
    parse_cobol_raw_handler,
)
from src.mcp_servers.common.tool_registry import register_tool

mcp = FastMCP("cobol_analysis")


@register_tool(
    domain="cobol_analysis",
    tool_name="parse_cobol",
    description="Parse COBOL source code into Abstract Syntax Tree (AST)",
)
@mcp.tool()
async def parse_cobol(
    source_code: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Parse COBOL source code into Abstract Syntax Tree (AST)."""
    return parse_cobol_handler({"source_code": source_code, "file_path": file_path})


@register_tool(
    domain="cobol_analysis",
    tool_name="parse_cobol_raw",
    description="Parse COBOL source code into raw ParseNode (parse tree) without building AST",
)
@mcp.tool()
async def parse_cobol_raw(
    source_code: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Parse COBOL source code into raw ParseNode (parse tree) without building AST."""
    return parse_cobol_raw_handler({"source_code": source_code, "file_path": file_path})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_ast",
    description="Build Abstract Syntax Tree (AST) from ParseNode",
)
@mcp.tool()
async def build_ast(parse_tree: dict[str, Any]) -> dict[str, Any]:
    """Build Abstract Syntax Tree (AST) from ParseNode."""
    return build_ast_handler({"parse_tree": parse_tree})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_cfg",
    description="Build Control Flow Graph (CFG) from AST",
)
@mcp.tool()
async def build_cfg(ast: dict[str, Any]) -> dict[str, Any]:
    """Build Control Flow Graph (CFG) from AST."""
    return build_cfg_handler({"ast": ast})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_dfg",
    description="Build Data Flow Graph (DFG) from AST + CFG",
)
@mcp.tool()
async def build_dfg(ast: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Build Data Flow Graph (DFG) from AST + CFG."""
    return build_dfg_handler({"ast": ast, "cfg": cfg})


@register_tool(
    domain="cobol_analysis",
    tool_name="build_pdg",
    description="Build Program Dependency Graph (PDG) from AST + CFG + DFG",
)
@mcp.tool()
async def build_pdg(
    ast: dict[str, Any],
    cfg: dict[str, Any],
    dfg: dict[str, Any],
) -> dict[str, Any]:
    """Build Program Dependency Graph (PDG) from AST + CFG + DFG."""
    return build_pdg_handler({"ast": ast, "cfg": cfg, "dfg": dfg})
```

#### Step 3.2: Update COBOL Server Entry Points

Update `mcp_cobol_analysis/__main__.py` and `mcp_cobol_analysis/http_main.py` to use decorators.

#### Step 3.3: Remove COBOL Manual Wrappers

Remove all COBOL-related wrapper functions from `dynamic_loader.py`.

---

### Phase 4: Cleanup and Documentation (Week 2, Days 4-5)

**Goal**: Remove legacy code and update documentation

#### Step 4.1: Deprecate Dynamic Loader

Mark `dynamic_loader.py` functions as deprecated:

```python
import warnings

def load_tools_from_database(...):
    """DEPRECATED: Use decorator-based registration instead.

    This function will be removed in a future version.
    Use load_tools_from_registry() instead.
    """
    warnings.warn(
        "load_tools_from_database() is deprecated. "
        "Use decorator-based registration with load_tools_from_registry() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # ... existing implementation ...
```

#### Step 4.2: Update Documentation

Update:
- `CLAUDE.md`: Update "Adding a New Tool" section
- `docs/ARCHITECTURE.md`: Document new tool registration pattern
- `README.md`: Update examples

#### Step 4.3: Remove Legacy Code

After all domains migrated:
- Remove `dynamic_loader.py` (or keep as fallback for 1 release)
- Remove `use_decorators` parameter (always use decorators)
- Remove manual wrapper functions

#### Step 4.4: Update Tool Service

Update `tool_service.py` to validate that tools exist in registry:

```python
async def create_tool(self, tool_data: ToolCreate) -> ToolResponse:
    """Create a new tool.

    Now validates that handler exists AND tool is registered in code.
    """
    # Check handler exists
    if not get_handler(tool_data.handler_name):
        raise ToolHandlerNotFoundError(...)

    # NEW: Check tool is registered in code (for decorator-based tools)
    from src.mcp_servers.common.tool_registry import TOOL_REGISTRY
    domain_tools = TOOL_REGISTRY.get(tool_data.domain, [])
    registered_names = {name for name, _, _ in domain_tools}

    if tool_data.name not in registered_names:
        raise ValidationError(
            f"Tool '{tool_data.name}' is not registered in code. "
            f"Add @register_tool() decorator in domain tools file."
        )

    # ... rest of creation logic ...
```

---

## Migration Checklist

### Phase 1: Foundation ✅ COMPLETED
- [x] Create `tool_registry.py` module
- [x] Create `mcp_general/tools.py` with echo and calculator_add
- [x] Update runners to support both systems (`use_decorators` flag)
- [x] Add tests for tool registry
- [x] Verify both old and new systems work

### Phase 2: General Domain ✅ COMPLETED
- [x] Complete `mcp_general/tools.py` with all tools
- [x] Update `mcp_general/__main__.py` to use decorators
- [x] Update `mcp_general/http_main.py` to use decorators
- [x] Remove general tool wrappers from `dynamic_loader.py`
- [x] Add integration tests (`test_decorator_integration.py`)
- [x] Verify all general tools work

### Phase 3: COBOL Domain ✅ COMPLETED
- [x] Create `mcp_cobol_analysis/tools.py` with all 6 COBOL tools
- [x] Update COBOL server entry points (`__main__.py` and `http_main.py`)
- [x] Remove COBOL tool wrappers from `dynamic_loader.py`
- [x] Add integration tests
- [x] Verify all COBOL tools work

### Phase 4: Cleanup 🔄 IN PROGRESS
- [x] Mark `load_tools_from_database()` as deprecated
- [x] Update CLAUDE.md documentation
- [ ] Run full test suite to verify nothing broke
- [ ] Update `tool_service.py` validation (OPTIONAL)
- [ ] Remove `use_decorators` flag (FUTURE: always use decorators)
- [ ] Remove legacy wrapper functions completely (FUTURE)

---

## Testing Strategy

### Unit Tests
- Test `tool_registry.py` functions
- Test tool registration and loading
- Test observability wrapping

### Integration Tests
- Test each domain's tools end-to-end
- Test database filtering (is_active)
- Test transport compatibility (stdio, http, sse)

### Manual Testing
- Test with Claude Desktop (STDIO)
- Test with MCP Inspector (HTTP/SSE)
- Verify observability metrics still work
- Verify database enable/disable works

---

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Set `use_decorators=False` in server entry points
2. **Partial Rollback**: Keep problematic domain on old system, migrate others
3. **Code Rollback**: Revert commits, restore `dynamic_loader.py` wrappers

**Safety**: Both systems coexist during migration, so rollback is low-risk.

---

## Benefits After Migration

1. **Scalability**: Adding tools requires only decorator + handler (2 steps vs 4)
2. **Type Safety**: Full IDE support and type checking
3. **Maintainability**: Single source of truth for tool implementation
4. **Performance**: No runtime DB queries for tool registration
5. **Developer Experience**: Clear, standard FastMCP pattern

---

## Questions and Considerations

### Q: What if we want to add tools dynamically at runtime?
**A**: Keep database-driven system for those specific tools. Most tools should be decorator-based.

### Q: How do we handle tool versioning?
**A**: Database can store version metadata. Decorators register current version.

### Q: What about tools that need complex parameter validation?
**A**: Use Pydantic models in tool signatures. FastMCP supports this.

### Q: Can we keep both systems?
**A**: Yes, during migration. Long-term, prefer decorators for all tools.

---

## Next Steps

1. Review and approve this migration plan
2. Create Phase 1 tasks/issues
3. Begin implementation with Phase 1
4. Schedule regular check-ins during migration
5. Plan celebration after successful migration! 🎉

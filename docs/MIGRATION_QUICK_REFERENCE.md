# Migration Quick Reference: Before & After

## Adding a New Tool: Before vs After

### ❌ Before (Database-Driven - 4 Steps)

**Step 1**: Create handler in `tool_handlers_service.py`
```python
def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "result": parameters.get("input")}
```

**Step 2**: Register in `TOOL_HANDLERS` dict
```python
TOOL_HANDLERS = {
    "my_tool_handler": my_tool_handler,
}
```

**Step 3**: Add database record in `scripts/seed_tools.py`
```python
ToolCreate(
    name="my_tool",
    handler_name="my_tool_handler",
    domain="general",
    # ... schema, description, etc.
)
```

**Step 4**: Create manual wrapper in `dynamic_loader.py`
```python
def _create_my_tool_tool(handler_func, tool_name, domain, transport):
    async def tool_impl(input: str) -> dict[str, Any]:
        result = handler_func({"input": input})
        return result
    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)
    return traced_tool

# Then add to register_tool_from_db():
elif tool.name == "my_tool":
    tool_func = _create_my_tool_tool(handler_func, tool.name, domain, transport)
```

**Total**: 4 files to modify, manual wrapper required

---

### ✅ After (Decorator-Based - 2 Steps)

**Step 1**: Create handler in `tool_handlers_service.py` (same as before)
```python
def my_tool_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "result": parameters.get("input")}
```

**Step 2**: Add decorator in domain `tools.py` file
```python
# src/mcp_servers/mcp_general/tools.py
from src.core.services.general.tool_handlers_service import my_tool_handler
from src.mcp_servers.common.tool_registry import register_tool

@register_tool(domain="general", tool_name="my_tool", description="Does X")
@mcp.tool()
async def my_tool(input: str) -> dict[str, Any]:
    """Does X with input text."""
    return my_tool_handler({"input": input})
```

**Optional Step 3**: Add database record for metadata/enable-disable
```python
# scripts/seed_tools.py (optional, for enable/disable control)
ToolCreate(
    name="my_tool",
    handler_name="my_tool_handler",  # Not used, but kept for compatibility
    domain="general",
    is_active=True,  # This controls whether tool is loaded
    # ... description, schema, etc.
)
```

**Total**: 2 files to modify, no manual wrapper needed!

---

## Code Comparison

### Handler Function (Unchanged)
```python
# src/core/services/general/tool_handlers_service.py
def echo_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    text = parameters.get("text", "")
    return {"success": True, "message": f"Echo: {text}"}
```

### Before: Manual Wrapper
```python
# src/mcp_servers/common/dynamic_loader.py
def _create_echo_tool(handler_func, tool_name, domain, transport):
    async def tool_impl(text: str) -> dict[str, Any]:
        result = handler_func({"text": text})
        return result
    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)
    async def echo_tool(text: str) -> dict[str, Any]:
        result = await traced(text)
        return result
    return echo_tool

# In register_tool_from_db():
elif tool.name == "echo":
    tool_func = _create_echo_tool(handler_func, tool.name, domain, transport)
```

### After: Decorator
```python
# src/mcp_servers/mcp_general/tools.py
@register_tool(domain="general", tool_name="echo", description="Echo text")
@mcp.tool()
async def echo(text: str) -> dict[str, Any]:
    """Echo back the provided text."""
    return echo_handler({"text": text})
```

**Benefits**:
- ✅ 10 lines → 4 lines
- ✅ Type-safe signature
- ✅ IDE autocomplete works
- ✅ No manual wrapper needed

---

## Complex Example: Multiple Parameters

### Before
```python
# Handler
def build_dfg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    ast = parameters.get("ast")
    cfg = parameters.get("cfg")
    # ... logic ...

# Wrapper (in dynamic_loader.py)
def _create_build_dfg_tool(handler_func, tool_name, domain, transport):
    async def tool_impl(ast: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        result = handler_func({"ast": ast, "cfg": cfg})
        return result
    traced = _create_traced_tool(tool_name, domain, transport, tool_impl)
    async def build_dfg_tool(ast: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        result = await traced(ast, cfg)
        return result
    return build_dfg_tool
```

### After
```python
# Handler (same)
def build_dfg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    ast = parameters.get("ast")
    cfg = parameters.get("cfg")
    # ... logic ...

# Decorator
@register_tool(domain="cobol_analysis", tool_name="build_dfg", description="Build DFG")
@mcp.tool()
async def build_dfg(ast: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Build Data Flow Graph (DFG) from AST + CFG."""
    return build_dfg_handler({"ast": ast, "cfg": cfg})
```

---

## Migration Steps for Existing Tools

1. **Find the tool** in `dynamic_loader.py` (look for `_create_*_tool` function)
2. **Copy the signature** (parameter names and types)
3. **Create decorator** in domain `tools.py` file
4. **Test** the tool works
5. **Remove** the manual wrapper from `dynamic_loader.py`
6. **Remove** the `elif` branch in `register_tool_from_db()`

---

## Common Patterns

### Optional Parameters
```python
@register_tool(domain="general", tool_name="my_tool")
@mcp.tool()
async def my_tool(
    required: str,
    optional: str | None = None,
) -> dict[str, Any]:
    """Tool with optional parameter."""
    return my_tool_handler({
        "required": required,
        "optional": optional,
    })
```

### Multiple Domains
```python
# General domain
# src/mcp_servers/mcp_general/tools.py
@register_tool(domain="general", tool_name="echo")
@mcp.tool()
async def echo(text: str) -> dict[str, Any]:
    ...

# COBOL domain
# src/mcp_servers/mcp_cobol_analysis/tools.py
@register_tool(domain="cobol_analysis", tool_name="parse_cobol")
@mcp.tool()
async def parse_cobol(source_code: str | None = None) -> dict[str, Any]:
    ...
```

---

## FAQ

**Q: Do I still need the database?**
A: Yes! Database controls enable/disable (`is_active` flag) and stores metadata for observability.

**Q: What if I want to disable a tool temporarily?**
A: Set `is_active=False` in database. Tool won't be registered even if decorator exists.

**Q: Can I use Pydantic models for parameters?**
A: Yes! FastMCP supports Pydantic models:
```python
from pydantic import BaseModel

class MyToolParams(BaseModel):
    input: str
    count: int = 1

@mcp.tool()
async def my_tool(params: MyToolParams) -> dict[str, Any]:
    return my_tool_handler(params.model_dump())
```

**Q: What about observability?**
A: Automatically applied! The `load_tools_from_registry()` function wraps all tools with observability tracing.

**Q: How do I test my tool?**
A: Same as before - tools are registered with FastMCP and can be tested via MCP clients.

---

## Need Help?

- See `docs/MIGRATION_PLAN_DECORATOR_BASED_TOOLS.md` for detailed migration plan
- Check existing tools in `src/mcp_servers/mcp_general/tools.py` for examples
- Review `src/mcp_servers/common/tool_registry.py` for implementation details

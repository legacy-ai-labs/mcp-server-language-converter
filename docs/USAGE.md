# Usage Guide

This guide shows you how to use the MCP Server Blueprint for common tasks.

## Quick Start

### 1. Set Up Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your database credentials
nano .env
```

### 2. Initialize Database

```bash
# Create tables
uv run python scripts/init_db.py

# Seed initial tools
uv run python scripts/seed_tools.py
```

### 3. Run MCP Server

```bash
# Run via STDIO (for use with AI clients like Claude Desktop)
uv run python -m src.mcp_servers.mcp_general

# Run via HTTP Streaming (for web-based AI clients)
uv run python -m src.mcp_servers.mcp_general.http_main

# Or use the startup script
uv run python scripts/start_http_streaming.py
```

## Testing the Server

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/core/test_tool_handlers.py

# Run with verbose output
uv run pytest -v
```

### Manual Testing with Python

```python
import asyncio
from src.core.database import async_session_factory
from src.core.services.tool_service_service import ToolService

async def test_echo_tool():
    async with async_session_factory() as session:
        service = ToolService(session)

        # Execute echo tool
        result = await service.execute_tool(
            "echo",
            {"text": "Hello, World!"}
        )

        print(result)

asyncio.run(test_echo_tool())
```

## Managing Tools

### List Available Tools

```python
import asyncio
from src.core.database import async_session_factory
from src.core.services.tool_service_service import ToolService

async def list_tools():
    async with async_session_factory() as session:
        service = ToolService(session)
        tools = await service.list_tools(active_only=True)

        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

asyncio.run(list_tools())
```

### Create a New Tool

```python
import asyncio
from src.core.database import async_session_factory
from src.core.services.tool_service_service import ToolService
from src.core.schemas.tool_schema import ToolCreate

async def create_tool():
    tool_data = ToolCreate(
        name="my_custom_tool",
        description="My custom tool description",
        handler_name="echo_handler",  # Must be a registered handler
        parameters_schema={
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        },
        is_active=True
    )

    async with async_session_factory() as session:
        service = ToolService(session)
        tool = await service.create_tool(tool_data)
        print(f"Created tool: {tool.name} (ID: {tool.id})")

asyncio.run(create_tool())
```

### Deactivate a Tool

```python
import asyncio
from src.core.database import async_session_factory
from src.core.services.tool_service_service import ToolService

async def deactivate_tool(tool_id: int):
    async with async_session_factory() as session:
        service = ToolService(session)
        await service.delete_tool(tool_id, soft=True)
        print(f"Tool {tool_id} deactivated")

asyncio.run(deactivate_tool(1))
```

## Using with AI Clients

### STDIO Mode (Claude Desktop, Cursor IDE)

#### Claude Desktop Configuration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-server-language-converter": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.mcp_servers.mcp_general"],
      "cwd": "/path/to/mcp-server-language-converter",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/mcp_server"
      }
    }
  }
}
```

#### Cursor IDE Configuration

Add to Cursor settings:

```json
{
  "mcp.servers": {
    "mcp-server-language-converter": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.mcp_servers.mcp_general"],
      "cwd": "/path/to/mcp-server-language-converter"
    }
  }
}
```

### HTTP Streaming Mode (Web-based AI Clients)

#### Configuration

HTTP streaming mode uses Server-Sent Events (SSE) for real-time communication:

```bash
# Start HTTP streaming server
uv run python -m src.mcp_servers.mcp_general.http_main

# Server will be available at:
# http://localhost:8000
```

#### Environment Variables

Configure HTTP streaming in `.env`:

```bash
# HTTP Streaming Configuration
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
HTTP_STREAMING_ENABLED=true
```

#### Client Integration

For web-based AI clients, connect to the HTTP streaming endpoint:

```javascript
// Example client connection
const eventSource = new EventSource('http://localhost:8000/sse');
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('MCP response:', data);
};
```

#### Testing HTTP Streaming

**Quick Test:**
```bash
# Test with curl
curl -N -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/sse

# Test with HTTPie
http --stream GET localhost:8000/sse
```

**Comprehensive Testing:**
For detailed testing instructions including MCP Inspector, browser testing, Python clients, and troubleshooting, see the [HTTP Streaming Guide](HTTP_STREAMING.md#testing-http-streaming).

## Creating Custom Handlers

### 1. Define Handler Function

Create a new handler in `src/core/services/tool_handlers_service.py`:

```python
def my_custom_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """My custom handler implementation.

    Args:
        parameters: Handler parameters

    Returns:
        Dictionary with result
    """
    # Your logic here
    value = parameters.get("input", "")

    return {
        "success": True,
        "result": f"Processed: {value}",
    }
```

### 2. Register Handler

Add to the `TOOL_HANDLERS` dictionary:

```python
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "echo_handler": echo_handler,
    "calculator_add_handler": calculator_add_handler,
    "my_custom_handler": my_custom_handler,  # Add your handler
}
```

### 3. Create Tool Using Handler

```python
from src.core.schemas.tool_schema import ToolCreate

tool_data = ToolCreate(
    name="my_tool",
    description="Uses my custom handler",
    handler_name="my_custom_handler",
    parameters_schema={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input value"}
        },
        "required": ["input"]
    }
)
```

## Logging

### Configure Log Level

Set in `.env`:

```
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### View Logs

Logs are output to stdout/stderr. Redirect to a file if needed:

```bash
uv run python -m src.mcp_server 2>&1 | tee server.log
```

## Troubleshooting

### Server Won't Start

1. Check database connection:
   ```bash
   psql $DATABASE_URL
   ```

2. Verify environment variables:
   ```bash
   cat .env
   ```

3. Check logs for errors

### Tool Not Found

1. Verify tool exists in database:
   ```sql
   SELECT * FROM tools WHERE name = 'tool_name';
   ```

2. Check if tool is active:
   ```sql
   SELECT is_active FROM tools WHERE name = 'tool_name';
   ```

3. Restart server to reload tools

### Handler Error

1. Check handler exists in registry:
   ```python
   from src.core.services.tool_handlers_service import list_handlers
   print(list_handlers())
   ```

2. Verify handler name matches in database

3. Check handler function signature

## Best Practices

1. **Always test handlers** before creating tools
2. **Use descriptive tool names** (lowercase, underscores)
3. **Provide detailed descriptions** for AI understanding
4. **Define complete parameter schemas** with descriptions
5. **Handle errors gracefully** in handlers
6. **Log important operations** for debugging
7. **Keep handlers stateless** when possible
8. **Validate input parameters** in handlers
9. **Return consistent response format** from handlers
10. **Restart server** after configuration changes

## Performance Tips

1. **Keep handlers fast** - avoid long-running operations
2. **Use connection pooling** (already configured)
3. **Cache frequently used data** if needed
4. **Monitor database connections**
5. **Use indexes** for custom queries

## Next Steps

- Explore [Architecture Documentation](ARCHITECTURE.md)
- Read [Database Guide](DATABASE.md)
- Review [Contributing Guidelines](CONTRIBUTING.md)
- Learn about [API Documentation](API.md)

---

For more advanced usage and development, see the other documentation files in the `docs/` directory.

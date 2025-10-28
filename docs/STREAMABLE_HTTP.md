# Streamable HTTP Transport Guide

This guide explains how to use the Streamable HTTP transport with our MCP Server Blueprint.

## Overview

Streamable HTTP is a bidirectional HTTP transport protocol that consolidates all client-server interactions through a single `/mcp` endpoint. It supports both immediate JSON responses and Server-Sent Events (SSE) for long-running operations.

## Key Features

- **Single Endpoint**: All communication happens through `/mcp`
- **Session Management**: Automatic session ID handling
- **Bidirectional**: Supports both client-to-server and server-to-client communication
- **Streaming**: Supports SSE for real-time updates
- **Stateless**: Each request can be independent (optional)

## Server Configuration

### Port Configuration

The Streamable HTTP server runs on port 8002 by default (configurable via environment variables):

```bash
# Default configuration
STREAMABLE_HTTP_HOST=0.0.0.0
STREAMABLE_HTTP_PORT=8002
STREAMABLE_HTTP_ENABLED=true
```

### Starting the Server

```bash
# Start Streamable HTTP server
uv run python -m src.mcp_servers.mcp_general.streamable_http_main

# Or use the startup script
uv run python scripts/start_streamable_http.py
```

## Client Usage

### Python Client (Recommended)

Use the official MCP client library for proper session handling:

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test_streamable_http():
    url = "http://127.0.0.1:8002/mcp"

    async with streamablehttp_client(url) as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize session
            init_result = await session.initialize()
            print(f"Connected to: {init_result.serverInfo.name}")

            # List available tools
            tools_result = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools_result.tools]}")

            # Call a tool
            result = await session.call_tool("echo", {"text": "Hello World!"})
            print(f"Result: {result.content[0].text}")

# Run the test
asyncio.run(test_streamable_http())
```

### Session Management

The MCP client automatically handles:
- **Session ID extraction** from `mcp-session-id` response headers
- **Session ID inclusion** in subsequent requests
- **Protocol version negotiation** during initialization
- **Connection cleanup** on session termination

## Protocol Details

### Request Format

All requests are POST requests to `/mcp` with:

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
mcp-session-id: <session-id>  # After first request

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

### Response Format

Responses include session management headers:

```http
HTTP/1.1 200 OK
Content-Type: application/json
mcp-session-id: <new-session-id>  # On first request

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { ... }
}
```

### Streaming Responses

For long-running operations, the server can send SSE events:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream

data: {"jsonrpc": "2.0", "method": "notifications/progress", "params": {...}}

data: {"jsonrpc": "2.0", "method": "notifications/complete", "params": {...}}
```

## Testing

### Test Scripts

We provide several test scripts:

```bash
# Test Streamable HTTP only
uv run python test_streamable_http_client.py

# Test both SSE and Streamable HTTP
uv run python test_both_transports.py

# Start both servers for testing
uv run python scripts/start_all_servers.py
```

### Manual Testing

You can test the server manually with curl:

```bash
# Get a session ID (first request)
curl -X POST http://127.0.0.1:8002/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}' \
  -v

# Use the session ID from the response header
curl -X POST http://127.0.0.1:8002/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <session-id-from-previous-response>" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}' \
  -v
```

## Comparison with SSE Transport

| Feature | SSE Transport | Streamable HTTP |
|---------|---------------|-----------------|
| **Endpoint** | `/sse` | `/mcp` |
| **Communication** | Server-to-client only | Bidirectional |
| **Session Management** | Automatic | Automatic |
| **Port** | 8000 | 8002 |
| **Use Case** | Real-time updates | Full MCP protocol |
| **Client Complexity** | Simple | Requires MCP client |

## Troubleshooting

### Common Issues

1. **"Missing session ID" errors**: Use the official MCP client library instead of manual HTTP requests
2. **Port conflicts**: Ensure port 8002 is available or change `STREAMABLE_HTTP_PORT`
3. **Connection refused**: Verify the server is running with `ps aux | grep streamable_http_main`

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Server Logs

Check server logs for detailed information:

```bash
# Server logs are sent to stderr
uv run python -m src.mcp_servers.mcp_general.streamable_http_main 2>&1 | tee server.log
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

app = FastAPI()

@app.post("/api/echo")
async def echo_text(text: str):
    async with streamablehttp_client("http://127.0.0.1:8002/mcp") as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("echo", {"text": text})
            return {"result": result.content[0].text}
```

### WebSocket Bridge

```python
# Bridge Streamable HTTP to WebSocket for web clients
import asyncio
import websockets
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def bridge_handler(websocket, path):
    async with streamablehttp_client("http://127.0.0.1:8002/mcp") as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Bridge messages between WebSocket and MCP
            async for message in websocket:
                # Forward WebSocket message to MCP
                # Forward MCP response to WebSocket
                pass

start_server = websockets.serve(bridge_handler, "localhost", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
```

## Best Practices

1. **Use the official MCP client library** for proper session handling
2. **Handle connection errors gracefully** with proper exception handling
3. **Implement reconnection logic** for production applications
4. **Monitor session lifecycle** to avoid resource leaks
5. **Use appropriate timeouts** for different operations
6. **Test with both immediate and streaming responses**

## Further Reading

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [FastMCP Documentation](https://gofastmcp.com)
- [HTTP Streaming Guide](./HTTP_STREAMING.md)
- [API Documentation](./API.md)

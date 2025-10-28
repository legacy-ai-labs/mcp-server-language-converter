# HTTP Streaming Guide

This guide covers HTTP streaming implementation for the MCP Server Blueprint, enabling web-based AI clients to interact with MCP tools via HTTP.

## Overview

HTTP streaming mode uses **Server-Sent Events (SSE)** to provide real-time, bidirectional communication between web-based AI clients and the MCP server. This allows AI applications running in browsers or web environments to access MCP tools without requiring STDIO transport.

## Understanding HTTP Streaming Protocols

### What is Server-Sent Events (SSE)?

**Server-Sent Events (SSE)** is a standard HTTP-based protocol that enables servers to push data to web clients over a single, long-lived HTTP connection. It's part of the HTML5 specification and provides a simple, efficient way to stream data from server to client.

**Key characteristics:**
- **Unidirectional**: Server → Client only (requests go via separate HTTP calls)
- **Text-based**: Events are UTF-8 encoded text
- **Auto-reconnection**: Built-in reconnection logic in browsers
- **Event IDs**: Support for resuming from last received event
- **Simple protocol**: Just HTTP with `Content-Type: text/event-stream`

**How SSE works:**
```
Client                          Server
  |                                |
  |--- HTTP GET /sse ------------->|
  |                                |
  |<-- HTTP 200 OK ----------------|
  |    Content-Type: text/event-stream
  |    Connection: keep-alive      |
  |                                |
  |<-- data: message 1 ------------|
  |<-- data: message 2 ------------|
  |<-- data: message 3 ------------|
  |          (connection stays open)
```

### SSE vs Other HTTP Streaming Protocols

#### Comparison Table

| Feature | **SSE** | **WebSockets** | **Long Polling** | **HTTP/2 Push** |
|---------|---------|----------------|------------------|-----------------|
| **Direction** | Server → Client | Bidirectional | Both (via polling) | Server → Client |
| **Protocol** | HTTP | WebSocket (ws://) | HTTP | HTTP/2 |
| **Connection** | Single long-lived | Single bidirectional | Multiple short | Multiple |
| **Reconnection** | Automatic | Manual | Manual | Automatic |
| **Browser Support** | Excellent | Excellent | Universal | Deprecated |
| **Firewall Friendly** | ✅ Yes (HTTP) | ⚠️ Sometimes blocked | ✅ Yes | ✅ Yes |
| **Complexity** | Low | Medium | Low | High |
| **Overhead** | Low | Very Low | High | Medium |
| **Use Case** | Server push, updates | Real-time chat, gaming | Legacy support | Proactive caching |

#### SSE vs WebSockets

**Server-Sent Events (SSE):**
- ✅ **Simpler**: Standard HTTP, no special protocol
- ✅ **Auto-reconnect**: Built into EventSource API
- ✅ **Firewall friendly**: Works everywhere HTTP works
- ✅ **HTTP/2 compatible**: Multiplexes over single connection
- ❌ **One-way**: Client can't send messages over the SSE connection
- ❌ **Text only**: No binary data support
- ✅ **Best for**: Server updates, notifications, streaming responses

**WebSockets:**
- ✅ **Bidirectional**: Full-duplex communication
- ✅ **Binary support**: Can send binary data
- ✅ **Lower latency**: No HTTP overhead after handshake
- ❌ **More complex**: Requires WebSocket protocol support
- ❌ **Firewall issues**: Some corporate firewalls block ws://
- ❌ **Manual reconnection**: Need to implement retry logic
- ✅ **Best for**: Chat, gaming, collaborative editing

#### SSE vs Long Polling

**Server-Sent Events (SSE):**
- ✅ **Single connection**: Maintains one long-lived connection
- ✅ **Lower latency**: Immediate message delivery
- ✅ **Less overhead**: No repeated connection setup
- ✅ **Efficient**: Better server resource usage
- ✅ **Simpler code**: EventSource API handles everything

**Long Polling:**
- ❌ **Multiple connections**: New connection for each message
- ❌ **Higher latency**: Delay between poll requests
- ❌ **More overhead**: Repeated HTTP handshakes
- ❌ **Resource intensive**: More server connections
- ✅ **Universal**: Works with any HTTP client
- ✅ **Best for**: Legacy systems without SSE support

#### SSE vs HTTP/2 Server Push

**Server-Sent Events (SSE):**
- ✅ **Still active**: Widely supported and maintained
- ✅ **Dynamic**: Can push any data anytime
- ✅ **Standardized**: Part of HTML5 spec
- ✅ **Event-driven**: Natural fit for streaming data

**HTTP/2 Server Push:**
- ❌ **Deprecated**: Chrome removed support in 2022
- ❌ **Static**: Only for pushing resources (CSS, JS)
- ❌ **Limited**: Can't push arbitrary data
- ❌ **Being phased out**: Not recommended for new projects

### Why This Project Uses SSE

This MCP server implementation chose **Server-Sent Events (SSE)** for several strategic reasons:

#### 1. **MCP Protocol Alignment**
- MCP is primarily **server-driven**: Server sends tool responses to clients
- Clients send tool requests via **separate HTTP POST** endpoints
- SSE's unidirectional nature matches this pattern perfectly

#### 2. **Simplicity**
```python
# SSE is built into FastMCP - just one line:
mcp.run(transport="sse")
```

#### 3. **Browser Native Support**
```javascript
// No libraries needed - works in all modern browsers
const eventSource = new EventSource('http://localhost:8000/sse');
eventSource.onmessage = (event) => console.log(event.data);
```

#### 4. **Excellent Firewall Compatibility**
- SSE uses standard HTTP/HTTPS
- Works through corporate proxies and firewalls
- No special ports or protocols to allowlist

#### 5. **HTTP/2 Benefits**
When used over HTTP/2, SSE benefits from:
- **Multiplexing**: Multiple SSE streams over one TCP connection
- **Header compression**: Reduced overhead
- **Better performance**: Compared to HTTP/1.1

#### 6. **Automatic Reconnection**
```javascript
// Browser automatically reconnects if connection drops
eventSource.addEventListener('error', () => {
  console.log('Connection lost - browser will auto-reconnect');
});
```

### When to Consider Alternatives

**Use WebSockets instead if:**
- ❌ You need bidirectional real-time communication (chat, gaming)
- ❌ You need to send binary data (images, files)
- ❌ You need very low latency (sub-10ms requirements)

**Use Long Polling instead if:**
- ❌ You need to support very old browsers (IE8 and below)
- ❌ You're working with systems that don't support SSE

**For this MCP server:** SSE is the optimal choice because:
- ✅ Clients make tool requests via HTTP POST (not SSE)
- ✅ Server streams tool results via SSE
- ✅ Perfect separation of concerns
- ✅ Simple, efficient, and well-supported

## Architecture

```mermaid
graph TB
    subgraph Client["Web-based AI Client"]
        Browser["Browser/Web App"]
        SSE["EventSource API"]
    end

    subgraph Server["MCP Server"]
        HTTP["HTTP Streaming Server"]
        MCP["FastMCP Server"]
        Tools["MCP Tools"]
    end

    subgraph Core["Core Business Logic"]
        Handlers["Tool Handlers"]
        DB["Database"]
    end

    Browser --> SSE
    SSE --> HTTP
    HTTP --> MCP
    MCP --> Tools
    Tools --> Handlers
    Handlers --> DB

    style Client fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
    style Server fill:#0d0d0d,stroke:#fff,stroke-width:2px,color:#fff
    style Core fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
    style Browser fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style SSE fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style HTTP fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style MCP fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style Tools fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style Handlers fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style DB fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
```

## Features

- **Real-time Communication**: Server-Sent Events for instant responses
- **Tool Access**: Full access to all MCP tools via HTTP
- **Web-friendly**: Works with any web-based AI client
- **Configurable**: Host, port, and other settings via environment variables
- **Logging**: Comprehensive logging for debugging and monitoring

## Quick Start

### 1. Start HTTP Streaming Server

```bash
# Using the module directly
uv run python -m src.mcp_servers.mcp_general.http_main

# Using the startup script
uv run python scripts/start_http_streaming.py
```

### 2. Configure Environment

Create or update `.env`:

```bash
# HTTP Streaming Configuration
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
HTTP_STREAMING_ENABLED=true

# Database (required for tool loading)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mcp_server
```

### 3. Test Connection

```bash
# Test with curl
curl -N -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/sse

# Test with HTTPie
http --stream GET localhost:8000/sse
```

## Testing HTTP Streaming

### Testing Options Overview

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **MCP Inspector** | Development & Debugging | ✅ GUI interface<br/>✅ Real-time monitoring<br/>✅ Tool discovery<br/>✅ Official tool | ❌ Requires Node.js<br/>❌ Web interface only |
| **curl** | Quick testing | ✅ Simple<br/>✅ No dependencies<br/>✅ Command line | ❌ Limited interaction<br/>❌ No GUI |
| **Browser** | Real-world testing | ✅ Native web environment<br/>✅ Custom client testing | ❌ Requires custom code<br/>❌ More complex setup |
| **Python client** | Automated testing | ✅ Programmatic<br/>✅ Integration tests | ❌ Requires coding<br/>❌ No GUI |

### 1. MCP Inspector (Recommended for Development)

**MCP Inspector** is the official tool from the Model Context Protocol team for testing MCP servers.

#### Installation & Usage

```bash
# No installation required - run directly
npx @modelcontextprotocol/inspector

# This will start a web interface at: http://localhost:3000
```

#### Configuration Steps

1. **Start your HTTP streaming server:**
   ```bash
   uv run python -m src.mcp_servers.mcp_general.http_main
   ```

2. **Launch MCP Inspector:**
   ```bash
   npx @modelcontextprotocol/inspector
   ```

3. **Configure connection in browser:**
   - Open `http://localhost:3000`
   - Select transport: `Server-Sent Events (SSE)`
   - Enter server URL: `http://localhost:8000/sse`
   - Click "Connect"

4. **Test your MCP tools:**
   - Browse available tools (echo, calculator_add)
   - Invoke tools with parameters
   - Monitor real-time responses
   - View communication logs

#### MCP Inspector Features

- **Tool Discovery**: Automatically lists all available MCP tools
- **Interactive Testing**: Fill-in forms for tool parameters
- **Real-time Monitoring**: Live log of MCP protocol messages
- **Multi-Transport Support**: Test both STDIO and HTTP streaming
- **Error Debugging**: Detailed error messages and connection status

### 2. Command Line Testing

#### curl Testing

```bash
# Basic connection test
curl -N -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/sse

# Verbose output for debugging
curl -v -N -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/sse

# Test with timeout
curl -N --max-time 30 -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/sse
```

#### HTTPie Testing

```bash
# Install HTTPie
pip install httpie

# Test connection
http --stream GET localhost:8000/sse

# Test with headers
http --stream GET localhost:8000/sse \
     Accept:text/event-stream \
     Cache-Control:no-cache
```

### 3. Browser Testing

Create a simple HTML test page:

```html
<!DOCTYPE html>
<html>
<head>
    <title>MCP HTTP Streaming Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        #output { border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: auto; }
        button { margin: 5px; padding: 10px; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>MCP HTTP Streaming Test</h1>
    <div>
        <button onclick="testConnection()">Test Connection</button>
        <button onclick="testEchoTool()">Test Echo Tool</button>
        <button onclick="testCalculatorTool()">Test Calculator Tool</button>
        <button onclick="clearOutput()">Clear Output</button>
    </div>
    <div id="output"></div>

    <script>
        let eventSource;
        const output = document.getElementById('output');

        function log(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const className = type === 'error' ? 'error' : type === 'success' ? 'success' : '';
            output.innerHTML += `<div class="${className}">[${timestamp}] ${message}</div>`;
            output.scrollTop = output.scrollHeight;
        }

        function testConnection() {
            log('🔄 Connecting to MCP server...');

            if (eventSource) {
                eventSource.close();
            }

            eventSource = new EventSource('http://localhost:8000/sse');

            eventSource.onopen = function() {
                log('✅ Connected to MCP server!', 'success');
            };

            eventSource.onmessage = function(event) {
                log(`📨 Received: ${event.data}`);
            };

            eventSource.onerror = function(error) {
                log(`❌ Connection error: ${error}`, 'error');
            };
        }

        function testEchoTool() {
            log('🔄 Testing echo tool...');
            // Note: This would need a proper MCP client implementation
            // For now, this is just a placeholder
            log('⚠️ Echo tool testing requires MCP client implementation');
        }

        function testCalculatorTool() {
            log('🔄 Testing calculator tool...');
            // Note: This would need a proper MCP client implementation
            // For now, this is just a placeholder
            log('⚠️ Calculator tool testing requires MCP client implementation');
        }

        function clearOutput() {
            output.innerHTML = '';
        }

        // Auto-connect on page load
        window.onload = function() {
            testConnection();
        };
    </script>
</body>
</html>
```

### 4. Python Client Testing

Create a test client for automated testing:

```python
# test_http_streaming_client.py
import asyncio
import aiohttp
import json
import time

class MCPHTTPStreamingClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def connect(self):
        """Connect to the HTTP streaming server."""
        self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(
                f"{self.base_url}/sse",
                headers={
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache'
                }
            ) as response:
                print(f"✅ Connected to MCP server")
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")

                # Listen for messages
                async for line in response.content:
                    if line:
                        message = line.decode('utf-8').strip()
                        if message:
                            print(f"📨 Received: {message}")

        except Exception as e:
            print(f"❌ Connection error: {e}")
        finally:
            if self.session:
                await self.session.close()

    async def test_connection(self, duration: int = 10):
        """Test connection for a specified duration."""
        print(f"🔄 Testing connection for {duration} seconds...")

        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}/sse",
                        headers={'Accept': 'text/event-stream'}
                    ) as response:
                        if response.status == 200:
                            print("✅ Connection successful")
                        else:
                            print(f"❌ Connection failed: {response.status}")
                break
            except Exception as e:
                print(f"❌ Connection error: {e}")
                await asyncio.sleep(1)

async def main():
    client = MCPHTTPStreamingClient()

    print("🚀 MCP HTTP Streaming Test Client")
    print("=" * 40)

    # Test connection
    await client.test_connection()

    # Connect and listen
    print("\n🔄 Connecting to server...")
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Node.js Client Testing

```javascript
// test_http_streaming.js
const EventSource = require('eventsource');

class MCPHTTPStreamingTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.eventSource = null;
    }

    connect() {
        console.log('🔄 Connecting to MCP server...');

        this.eventSource = new EventSource(`${this.baseUrl}/sse`);

        this.eventSource.onopen = () => {
            console.log('✅ Connected to MCP server');
        };

        this.eventSource.onmessage = (event) => {
            console.log('📨 Received:', event.data);
        };

        this.eventSource.onerror = (error) => {
            console.error('❌ Connection error:', error);
        };
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            console.log('🔌 Disconnected from MCP server');
        }
    }

    testConnection(duration = 10000) {
        console.log(`🔄 Testing connection for ${duration/1000} seconds...`);

        this.connect();

        setTimeout(() => {
            this.disconnect();
            console.log('✅ Test completed');
        }, duration);
    }
}

// Usage
const tester = new MCPHTTPStreamingTester();
tester.testConnection(30000); // Test for 30 seconds
```

### Testing Workflow Recommendations

#### For Development:
1. **Start with MCP Inspector** - Great for initial testing and tool discovery
2. **Use curl for quick checks** - Fast connection testing
3. **Custom browser client** - For real-world web scenarios

#### For Production:
1. **Automated tests** - Python/JavaScript clients
2. **Health monitoring** - curl-based health checks
3. **Load testing** - Custom performance tests

### Troubleshooting Common Issues

#### Connection Refused
```bash
# Check if server is running
netstat -tlnp | grep 8000

# Check server logs
tail -f http_streaming.log
```

#### CORS Issues (Browser Testing)
```bash
# Test with curl first to verify server is working
curl -N -H "Accept: text/event-stream" http://localhost:8000/sse
```

#### Database Connection Issues
```bash
# Verify database is running
psql $DATABASE_URL -c "SELECT COUNT(*) FROM tools;"

# Reinitialize if needed
uv run python scripts/init_db.py
uv run python scripts/seed_tools.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HTTP_HOST` | `0.0.0.0` | Host to bind the HTTP server |
| `HTTP_PORT` | `8000` | Port for the HTTP server |
| `HTTP_STREAMING_ENABLED` | `true` | Enable HTTP streaming mode |
| `LOG_LEVEL` | `INFO` | Logging level |

### Server Settings

The HTTP streaming server uses FastMCP's SSE transport:

```python
mcp.run(
    transport="sse",
    show_banner=True,
    host=settings.http_host,
    port=settings.http_port,
)
```

## Client Integration

### JavaScript/TypeScript

```javascript
// Connect to HTTP streaming server
const eventSource = new EventSource('http://localhost:8000/sse');

// Handle MCP responses
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('MCP response:', data);

    // Handle different message types
    switch (data.type) {
        case 'tool_result':
            handleToolResult(data);
            break;
        case 'error':
            handleError(data);
            break;
    }
};

// Handle connection events
eventSource.onopen = function() {
    console.log('Connected to MCP server');
};

eventSource.onerror = function(error) {
    console.error('Connection error:', error);
};

// Send tool request
function callTool(toolName, parameters) {
    const request = {
        type: 'tool_call',
        tool: toolName,
        parameters: parameters
    };

    // Send via fetch or WebSocket if available
    fetch('/api/mcp/tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });
}
```

### Python Client

```python
import requests
import json

class MCPHTTPClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def call_tool(self, tool_name: str, parameters: dict) -> dict:
        """Call an MCP tool via HTTP streaming."""
        response = self.session.post(
            f"{self.base_url}/api/mcp/tool",
            json={
                "type": "tool_call",
                "tool": tool_name,
                "parameters": parameters
            }
        )
        return response.json()

    def stream_responses(self):
        """Stream responses from the server."""
        response = self.session.get(
            f"{self.base_url}/sse",
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )

        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                yield data

# Usage
client = MCPHTTPClient()

# Call a tool
result = client.call_tool("echo", {"text": "Hello, World!"})
print(result)

# Stream responses
for response in client.stream_responses():
    print(f"Stream: {response}")
```

## Available Tools

The HTTP streaming server provides access to all registered MCP tools:

### Echo Tool

```javascript
// Call echo tool
const result = await callTool("echo", {
    text: "Hello from HTTP streaming!"
});
// Result: { success: true, result: "Hello from HTTP streaming!" }
```

### Calculator Tool

```javascript
// Call calculator tool
const result = await callTool("calculator_add", {
    a: 5,
    b: 3
});
// Result: { success: true, result: 8 }
```

## Error Handling

### Server Errors

```javascript
eventSource.onerror = function(error) {
    console.error('Connection error:', error);

    // Handle different error types
    if (error.type === 'error') {
        // Connection lost
        console.log('Attempting to reconnect...');
        setTimeout(() => {
            eventSource = new EventSource('http://localhost:8000/sse');
        }, 5000);
    }
};
```

### Tool Errors

```javascript
function handleToolResult(data) {
    if (data.success) {
        console.log('Tool executed successfully:', data.result);
    } else {
        console.error('Tool execution failed:', data.error);
    }
}
```

## Monitoring and Debugging

### Logs

HTTP streaming server logs to stderr:

```bash
# View logs in real-time
uv run python -m src.mcp_servers.mcp_general.http_main 2>&1 | tee http_streaming.log

# Filter for specific events
uv run python -m src.mcp_servers.mcp_general.http_main 2>&1 | grep "tool"
```

### Health Check

```bash
# Check if server is running
curl -I http://localhost:8000/health

# Check server status
curl http://localhost:8000/status
```

### Performance Monitoring

```python
import time
import requests

def benchmark_tool_call(tool_name: str, parameters: dict, iterations: int = 100):
    """Benchmark tool execution performance."""
    client = MCPHTTPClient()

    start_time = time.time()
    for _ in range(iterations):
        client.call_tool(tool_name, parameters)
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations
    print(f"Average execution time: {avg_time:.3f}s")
    print(f"Throughput: {1/avg_time:.1f} calls/second")

# Benchmark echo tool
benchmark_tool_call("echo", {"text": "test"}, 100)
```

## Security Considerations

### CORS Configuration

For production deployments, configure CORS properly:

```python
# In your HTTP streaming server configuration
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Authentication

Implement authentication for production use:

```python
# Add authentication middleware
@app.middleware("http")
async def authenticate_request(request: Request, call_next):
    # Verify authentication token
    token = request.headers.get("Authorization")
    if not verify_token(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    response = await call_next(request)
    return response
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if server is running
   netstat -tlnp | grep 8000

   # Check logs
   tail -f http_streaming.log
   ```

2. **Tool Not Found**
   ```bash
   # Verify tools are loaded
   uv run python -c "
   from src.mcp_servers.mcp_general.dynamic_tools import load_tools_from_database
   import asyncio
   asyncio.run(load_tools_from_database())
   "
   ```

3. **Database Connection Issues**
   ```bash
   # Test database connection
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM tools;"
   ```

### Debug Mode

Enable debug logging:

```bash
# Set debug level
export LOG_LEVEL=DEBUG

# Run with debug output
uv run python -m src.mcp_servers.mcp_general.http_main
```

## Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
uv add gunicorn

# Run with gunicorn
gunicorn src.mcp_servers.mcp_general.http_main:app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker
```

### Using Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "src.mcp_servers.mcp_general.http_main"]
```

### Load Balancing

For high-traffic deployments, use a load balancer:

```nginx
upstream mcp_servers {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://mcp_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Next Steps

- Explore [REST API Documentation](API.md) for additional HTTP endpoints
- Review [Architecture Documentation](ARCHITECTURE.md) for system design
- Check [Contributing Guidelines](CONTRIBUTING.md) for development practices

---

For more information about MCP protocol and HTTP streaming, see the [Model Context Protocol specification](https://modelcontextprotocol.io/).

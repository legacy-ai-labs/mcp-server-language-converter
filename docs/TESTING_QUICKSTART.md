## MCP Testing Quickstart

Minimal steps to test all transports with MCP Inspector.

### Launch MCP Inspector UI
```bash
npx @modelcontextprotocol/inspector
```
Open http://localhost:3000 in your browser, then connect each transport using the commands/URLs below.

### STDIO (Claude Desktop/Cursor style)
1) Start server (keep running):
```bash
uv run python scripts/start_stdio.py
```
2) MCP Inspector → Transport: STDIO
   - Command: `uv run python scripts/start_stdio.py`
   - Working dir: `/Users/hyalen/workspace/mcp-server-language-converter`
3) Test:
   - Initialize → List tools → Call `echo` with `{ "text": "hello" }`

**Alternative (using module directly):**
```bash
uv run python -m src.mcp_servers.mcp_general
```

**Alternative (with environment variables and explicit directory):**
```bash
npx @modelcontextprotocol/inspector \
  -e DATABASE_URL="postgresql+asyncpg://user@localhost:5432/mcp_server" \
  -e LOG_LEVEL="INFO" \
  -- \
  uv --directory /path/to/mcp-server-language-converter \
     run python -m src.mcp_servers.mcp_general
```
> **Note:** This is an example command. Update the `DATABASE_URL`, directory path, and module path according to your MCP server configuration.

**MCP Inspector Configuration (if using UI):**
- Command: `uv`
- Arguments: `--directory /path/to/mcp-server-language-converter run python -m src.mcp_servers.mcp_general`
- Working Directory: `/path/to/mcp-server-language-converter`
> **Note:** Replace `/path/to/mcp-server-language-converter` with your actual project directory path.

### SSE (Server‑Sent Events)
1) Start server:
```bash
uv run python scripts/start_sse.py
```
2) MCP Inspector → Transport: Server‑Sent Events (SSE)
   - URL: `http://127.0.0.1:8000/sse`
3) Test:
   - Initialize → List tools → Call `echo`, `calculator_add`

**Alternative (using module directly):**
```bash
uv run python -m src.mcp_servers.mcp_general.http_main
```

### Streamable HTTP (recommended for web/microservices)
1) Start server:
```bash
uv run python scripts/start_streamable_http.py
```
2) MCP Inspector → Transport: Streamable HTTP
   - URL: `http://127.0.0.1:8002/mcp`
3) Test:
   - Initialize → List tools → Call `echo`, `calculator_add`

**Alternative (using module directly):**
```bash
uv run python -m src.mcp_servers.mcp_general.streamable_http_main
```

Notes
- If a port is busy, stop the other process or change the port via env vars.
- Browsers may hit CORS limits for SSE; MCP Inspector and Python clients work.

### HTML Test Page (optional)

Open the bundled page for a simple UI:
```bash
open ./test_streamable_http.html
```
- Lets you toggle between SSE and Streamable HTTP views.
- For SSE in a browser you may hit CORS limits; prefer MCP Inspector or Python clients.
- For Streamable HTTP, follow the on‑page instructions or use the Python client.

### Managing running MCP processes (macOS)

Check if servers are running (ports):
```bash
lsof -i :8000 -sTCP:LISTEN
lsof -i :8002 -sTCP:LISTEN
```

Get only PIDs and kill them:
```bash
lsof -ti:8000,8002 | xargs -r kill
```

Kill by script name (recommended):
```bash
pkill -f "scripts/start_sse.py" || true
pkill -f "scripts/start_streamable_http.py" || true
pkill -f "scripts/start_stdio.py" || true
```

Kill by module name (fallback):
```bash
pkill -f "src.mcp_servers.mcp_general.http_main" || true
pkill -f "src.mcp_servers.mcp_general.streamable_http_main" || true
pkill -f "src.mcp_servers.mcp_general" || true
```

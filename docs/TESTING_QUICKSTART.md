## MCP Testing Quickstart

Minimal steps to test all transports with MCP Inspector.

### Unified Server Runner

The unified server runner provides a single, protocol-agnostic way to run MCP servers with any transport protocol (stdio, sse, or streamable-http). It automatically handles transport-specific configuration including CORS middleware for SSE and host/port settings for HTTP-based transports.

**Key Benefits:**
- Single code path for all three protocols
- Automatic transport-specific configuration
- Backward compatible with existing entry points
- Simplified maintenance with one implementation

**Transport Options:**
- `stdio`: Standard input/output (for Claude Desktop, Cursor IDE)
- `sse`: Server-Sent Events (HTTP streaming with SSE)
- `streamable-http`: Streamable HTTP (recommended for web deployments)

**Note:** FastMCP's `run()` method only supports one transport at a time. The unified runner allows you to choose the transport at runtime, but you still need separate processes if you want to run multiple transports simultaneously.

### Launch MCP Inspector UI
```bash
npx @modelcontextprotocol/inspector
```
Open http://localhost:3000 in your browser, then connect each transport using the commands/URLs below.

### STDIO (Claude Desktop/Cursor style)

```bash
# General domain
uv run python -m src.mcp_servers.mcp_general stdio

# COBOL Analysis domain
uv run python -m src.mcp_servers.mcp_cobol_analysis stdio
```

**MCP Inspector Configuration:**
- Transport: STDIO
- Command: `uv run python -m src.mcp_servers.mcp_general stdio` (or `mcp_cobol_analysis`)
- Working dir: Your project root directory

**Test:**
- General: Initialize → List tools → Call `echo` with `{ "text": "hello" }`
- COBOL: Initialize → List tools → Call `parse_cobol` with a COBOL file path

### SSE (Server-Sent Events)

```bash
# General domain (port 8000)
uv run python -m src.mcp_servers.mcp_general sse

# COBOL Analysis domain (port 8001)
uv run python -m src.mcp_servers.mcp_cobol_analysis sse
```

**MCP Inspector Configuration:**
- Transport: Server-Sent Events (SSE)
- URL (General): `http://localhost:8000/sse`
- URL (COBOL): `http://localhost:8001/sse`

**Test:**
- General: Initialize → List tools → Call `echo`, `calculator_add`
- COBOL: Initialize → List tools → Call `build_asg`, `analyze_complexity`

### Streamable HTTP (recommended for web/microservices)

```bash
# General domain (port 8002)
uv run python -m src.mcp_servers.mcp_general streamable-http

# COBOL Analysis domain (port 8003)
uv run python -m src.mcp_servers.mcp_cobol_analysis streamable-http
```

**MCP Inspector Configuration:**
- Transport: Streamable HTTP
- URL (General): `http://localhost:8002/mcp`
- URL (COBOL): `http://localhost:8003/mcp`

**Test:**
- General: Initialize → List tools → Call `echo`, `calculator_add`
- COBOL: Initialize → List tools → Call `build_asg`, `analyze_complexity`

### Notes
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
lsof -i :8000 -sTCP:LISTEN  # SSE General
lsof -i :8001 -sTCP:LISTEN  # SSE COBOL
lsof -i :8002 -sTCP:LISTEN  # Streamable HTTP General
lsof -i :8003 -sTCP:LISTEN  # Streamable HTTP COBOL
lsof -i :9090 -sTCP:LISTEN  # Health/Metrics
```

Get only PIDs and kill them:
```bash
lsof -ti:8000,8001,8002,8003,9090 | xargs -r kill
```

Kill by module name:
```bash
pkill -f "src.mcp_servers.mcp_general" || true
pkill -f "src.mcp_servers.mcp_cobol_analysis" || true
```

---

## ProLeap COBOL Parser Scripts

These scripts use the ProLeap COBOL Parser (Java) to export AST and ASG structures to JSON. Useful for validating Python parser implementations.

### Prerequisites
- Java 17+
- Maven 3+
- Git

The scripts will automatically clone and build ProLeap on first run.

### Export AST (Abstract Syntax Tree)

The AST is the raw ANTLR parse tree with every grammar rule and token.

```bash
uv run python scripts/proleap_ast_export.py <cobol_file>
```

Example:
```bash
uv run python scripts/proleap_ast_export.py tests/cobol_samples/inter_program_test/programs/CUSTOMER-MGMT.cbl
```

Output: `output/proleap/<filename>.ast.json`

### Export ASG (Abstract Semantic Graph)

The ASG includes resolved references, symbol tables, and semantic information.

```bash
uv run python scripts/proleap_asg_export.py <cobol_file>
```

Example:
```bash
uv run python scripts/proleap_asg_export.py tests/cobol_samples/inter_program_test/programs/CUSTOMER-MGMT.cbl
```

Output: `output/proleap/<filename>.asg.json`

### What Each Export Provides

| Feature | AST | ASG |
|---------|-----|-----|
| Parse tree structure | Yes | No |
| Token positions (line/column) | Yes | No |
| Grammar rule names | Yes | No |
| Program name | No | Yes |
| Data hierarchy (variables) | No | Yes |
| Paragraphs & statements | No | Yes |
| CALL targets (inter-program) | No | Yes |

### Copybook Resolution

Both scripts auto-detect copybook directories in these locations:
- `../copybooks/` (relative to COBOL file)
- `./copybooks/`
- `../copy/`
- `./copy/`

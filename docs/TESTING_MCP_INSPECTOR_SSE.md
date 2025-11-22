# Testing MCP Server with MCP Inspector (SSE Transport)

This guide provides step-by-step instructions for testing your MCP server using MCP Inspector with Server-Sent Events (SSE) transport.

## Overview

**MCP Inspector** is the official tool from the Model Context Protocol team for testing and debugging MCP servers. It provides a web-based GUI that lets you:
- Connect to MCP servers via different transports (STDIO, SSE, Streamable HTTP)
- Browse available tools
- Test tool calls with parameters
- Monitor real-time communication logs
- Debug connection issues

**SSE (Server-Sent Events)** is perfect for web-based testing because:
- Uses standard HTTP (works through firewalls)
- Real-time streaming responses
- Browser-native support
- Simple to configure

---

## Prerequisites Checklist

Before starting, ensure you have:

- ✅ **PostgreSQL database** running and accessible
- ✅ **Database initialized** with tables and tools seeded
- ✅ **Python 3.12+** installed
- ✅ **UV package manager** installed
- ✅ **Node.js** installed (for running MCP Inspector)
- ✅ **Port 8000** available (default HTTP streaming port)

---

## Step 1: Verify Database Setup

The MCP server loads tools from the database at startup. Let's verify everything is ready:

### 1.1 Check Database Connection

```bash
# Test database connection (adjust URL if needed)
psql postgresql://postgres:postgres@localhost:5432/mcp_server -c "SELECT version();"
```

**Expected output:** PostgreSQL version information

**If connection fails:**
- Ensure PostgreSQL is running: `brew services start postgresql` (macOS) or `sudo systemctl start postgresql` (Linux)
- Check your `DATABASE_URL` environment variable matches your PostgreSQL setup
- Verify database exists: `createdb mcp_server` (if needed)

### 1.2 Initialize Database (If Not Done)

```bash
# Create database tables
uv run python scripts/init_db.py

# Seed initial tools
uv run python scripts/seed_tools.py
```

**Expected output:**
```
Database initialized successfully
Tools seeded successfully
```

### 1.3 Verify Tools Are Loaded

```bash
# Check tools in database
./scripts/db.sh tools-active
```

**Expected output:** List of active tools (e.g., `echo`, `calculator_add`, etc.)

**If no tools appear:**
- Run `uv run python scripts/seed_tools.py` again
- Check `./scripts/db.sh tools` to see all tools (including inactive ones)

---

## Step 2: Start the HTTP Streaming Server

The HTTP streaming server uses SSE transport and runs on port 8000 by default.

### 2.1 Check Port Availability

```bash
# Check if port 8000 is already in use
lsof -i :8000 -sTCP:LISTEN
```

**If port is busy:**
- Stop the process using that port: `lsof -ti:8000 | xargs kill`
- Or change the port via environment variable: `export HTTP_PORT=8001`

### 2.2 Start the Server

Open a **new terminal window** and run:

```bash
# Navigate to project root
cd /Users/hyalen/workspace/mcp-server-blueprint

# Start HTTP streaming server
uv run python -m src.mcp_servers.mcp_general.http_main
```

**Expected output:**
```
HTTP Streaming MCP Server starting for domain: general...
INFO:__main__:Running MCP server with HTTP streaming for domain: general
INFO:__main__:Prometheus metrics initialized
INFO:__main__:Loading tools for domain: general, transport: http
INFO:__main__:Loaded tool: echo
INFO:__main__:Loaded tool: calculator_add
INFO:__main__:Tools loaded successfully for domain: general
INFO:__main__:CORS enabled for SSE transport - browser connections allowed
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Key indicators of success:**
- ✅ "Tools loaded successfully for domain: general"
- ✅ "CORS enabled for SSE transport"
- ✅ "Uvicorn running on http://0.0.0.0:8000"

**Keep this terminal window open** - the server must stay running for testing.

### 2.3 Verify Server is Responding

In a **new terminal**, test the server:

```bash
# Quick health check (should return 200 OK)
curl -I http://localhost:8000/sse

# Test SSE endpoint (will stream events)
curl -N -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/sse
```

**Expected:** Connection established, server sends SSE events

**If connection fails:**
- Check server logs in the first terminal for errors
- Verify database connection: `./scripts/db.sh tools-active`
- Check firewall settings

---

## Step 3: Install and Launch MCP Inspector

MCP Inspector is a Node.js tool that runs in your browser.

### 3.1 Launch MCP Inspector

Open a **new terminal** (keep server running) and run:

```bash
# Launch MCP Inspector (no installation needed - uses npx)
npx @modelcontextprotocol/inspector
```

**Expected output:**
```
Need to install the following packages:
@modelcontextprotocol/inspector
Ok to proceed? (y)
```

Type `y` and press Enter.

**After installation:**
```
MCP Inspector is running at http://localhost:3000
```

**Note:** First run downloads the package (~10-30 seconds). Subsequent runs are instant.

### 3.2 Open MCP Inspector in Browser

1. **Open your web browser** (Chrome, Firefox, Safari, or Edge)
2. **Navigate to:** `http://localhost:3000`
3. **You should see:** MCP Inspector interface with connection options

**If browser doesn't open automatically:**
- Manually navigate to `http://localhost:3000`
- Check terminal for the exact URL if different

---

## Step 4: Configure Connection in MCP Inspector

Now we'll connect MCP Inspector to your running server.

### 4.1 Select Transport Type

In the MCP Inspector interface:

1. **Find the "Transport" dropdown** (usually at the top)
2. **Select:** `Server-Sent Events (SSE)` or `SSE`

**Visual guide:**
```
┌─────────────────────────────────────┐
│  MCP Inspector                      │
├─────────────────────────────────────┤
│  Transport: [Server-Sent Events ▼] │  ← Select this
│  URL: [________________]            │
│  [Connect]                          │
└─────────────────────────────────────┘
```

### 4.2 Enter Server URL

In the URL field, enter:

```
http://localhost:8000/sse
```

**Important notes:**
- Use `localhost` (not `127.0.0.1`) for better browser compatibility
- Port `8000` is the default HTTP streaming port
- Path `/sse` is the SSE endpoint
- Use `http://` (not `https://`) for local development

### 4.3 Connect to Server

1. **Click the "Connect" button**
2. **Wait for connection** (usually 1-2 seconds)

**Success indicators:**
- ✅ Connection status changes to "Connected" (green)
- ✅ "Initialize" button becomes available
- ✅ No error messages appear

**If connection fails:**
- Check server is running (Step 2.2)
- Verify URL is exactly `http://localhost:8000/sse`
- Check browser console for errors (F12 → Console tab)
- Try `http://127.0.0.1:8000/sse` if `localhost` doesn't work

---

## Step 5: Initialize the MCP Session

After connecting, you need to initialize the MCP protocol handshake.

### 5.1 Click Initialize

1. **Find the "Initialize" button** (usually prominent in the interface)
2. **Click it**

**Expected result:**
- ✅ Server capabilities appear (tools, resources, prompts)
- ✅ Available tools list populates
- ✅ Connection log shows initialization messages

**What happens:**
- MCP Inspector sends an `initialize` request
- Server responds with its capabilities
- Tools are discovered and listed

**If initialization fails:**
- Check server logs for errors
- Verify database has active tools: `./scripts/db.sh tools-active`
- Try disconnecting and reconnecting

---

## Step 6: Test Tools

Now you can test individual MCP tools!

### 6.1 Browse Available Tools

After initialization, you should see a list of tools:

- `echo` - Echoes back the input text
- `calculator_add` - Adds two numbers
- (Other tools you've seeded)

### 6.2 Test the Echo Tool

1. **Click on `echo`** in the tools list
2. **Fill in the parameters:**
   ```json
   {
     "text": "Hello from MCP Inspector!"
   }
   ```
3. **Click "Call Tool" or "Execute"**

**Expected result:**
- ✅ Response appears showing: `{"success": true, "result": "Hello from MCP Inspector!"}`
- ✅ Connection log shows the request/response
- ✅ No errors

**What to look for:**
- Response format matches expected schema
- Execution time is reasonable (< 1 second)
- No error messages in logs

### 6.3 Test the Calculator Tool

1. **Click on `calculator_add`** in the tools list
2. **Fill in the parameters:**
   ```json
   {
     "a": 42,
     "b": 8
   }
   ```
3. **Click "Call Tool"**

**Expected result:**
- ✅ Response: `{"success": true, "result": 50}`
- ✅ Correct calculation (42 + 8 = 50)

### 6.4 Test Error Handling

Test with invalid parameters:

1. **Call `calculator_add` with missing parameter:**
   ```json
   {
     "a": 5
   }
   ```
2. **Observe the error response**

**Expected:** Clear error message indicating missing parameter

---

## Step 7: Monitor Real-Time Logs

MCP Inspector shows all protocol messages in real-time.

### 7.1 View Connection Logs

- **Find the "Logs" or "Messages" panel**
- **Observe messages** as you interact with tools:
  - `initialize` request/response
  - `tools/list` request/response
  - `tools/call` requests/responses
  - Error messages (if any)

### 7.2 Understand Log Format

Logs typically show:
- **Request:** What MCP Inspector sent to server
- **Response:** What server sent back
- **Timestamps:** When each message occurred
- **Status:** Success or error indicators

---

## Step 8: Troubleshooting Common Issues

### Issue: "Connection Refused"

**Symptoms:** Can't connect to server

**Solutions:**
1. Verify server is running: Check terminal from Step 2.2
2. Check port: `lsof -i :8000 -sTCP:LISTEN`
3. Try different URL: `http://127.0.0.1:8000/sse`
4. Check firewall settings

### Issue: "No Tools Available"

**Symptoms:** Initialize succeeds but no tools appear

**Solutions:**
1. Check database has tools: `./scripts/db.sh tools-active`
2. Verify tools are active: `is_active=True` in database
3. Check domain matches: Tools must have `domain="general"`
4. Restart server after database changes

### Issue: "CORS Error" (Browser Console)

**Symptoms:** Browser blocks connection due to CORS

**Solutions:**
1. Verify CORS is enabled in server logs: "CORS enabled for SSE transport"
2. Check server code has CORS middleware (should be automatic)
3. Try MCP Inspector (handles CORS better than raw browser)

### Issue: "Tool Execution Failed"

**Symptoms:** Tool call returns error

**Solutions:**
1. Check parameter format matches schema
2. Verify handler function exists in `tool_handlers_service.py`
3. Check server logs for detailed error messages
4. Verify wrapper function exists in `dynamic_loader.py`

### Issue: "Database Connection Error"

**Symptoms:** Server fails to start, database errors

**Solutions:**
1. Verify PostgreSQL is running
2. Check `DATABASE_URL` environment variable
3. Test connection: `psql $DATABASE_URL -c "SELECT 1;"`
4. Reinitialize database: `uv run python scripts/init_db.py`

---

## Step 9: Clean Shutdown

When finished testing:

### 9.1 Disconnect from MCP Inspector

1. **Click "Disconnect"** in MCP Inspector
2. **Close browser tab** (optional)

### 9.2 Stop the Server

In the terminal running the server (Step 2.2):

1. **Press `Ctrl+C`** (or `Cmd+C` on macOS)
2. **Wait for graceful shutdown**

**Expected output:**
```
INFO:     Shutting down
INFO:     Application shutdown complete.
INFO:     Finished server process [xxxxx]
```

### 9.3 Stop MCP Inspector

In the terminal running MCP Inspector (Step 3.1):

1. **Press `Ctrl+C`** (or `Cmd+C` on macOS)

---

## Quick Reference Commands

### Start Server
```bash
uv run python -m src.mcp_servers.mcp_general.http_main
```

### Launch MCP Inspector
```bash
npx @modelcontextprotocol/inspector
```

### Check Database
```bash
./scripts/db.sh tools-active
```

### Test Server Connection
```bash
curl -I http://localhost:8000/sse
```

### Check Port Usage
```bash
lsof -i :8000 -sTCP:LISTEN
```

### Kill Process on Port
```bash
lsof -ti:8000 | xargs kill
```

---

## Next Steps

After successfully testing with MCP Inspector:

1. **Test with Claude Desktop** - See `docs/TESTING_GUIDE.md`
2. **Test with Cursor IDE** - Similar to Claude Desktop
3. **Test Streamable HTTP transport** - See `docs/TESTING_QUICKSTART.md`
4. **Add more tools** - Follow the 4-step process in `CLAUDE.md`
5. **Review observability** - Check Prometheus metrics and execution logs

---

## Summary

You've successfully:
- ✅ Started the HTTP streaming server with SSE transport
- ✅ Launched MCP Inspector
- ✅ Connected to your MCP server
- ✅ Initialized the MCP session
- ✅ Tested multiple tools
- ✅ Monitored real-time communication

**Your MCP server is working correctly!** 🎉

For more advanced testing scenarios, see:
- `docs/TESTING_GUIDE.md` - Claude Desktop integration
- `docs/HTTP_STREAMING.md` - Detailed HTTP streaming documentation
- `docs/TESTING_QUICKSTART.md` - Quick reference for all transports

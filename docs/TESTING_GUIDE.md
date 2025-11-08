# Testing with Claude Desktop

## Setup Complete ✅

Your MCP Server is now ready to test! Here's what you need:

- ✅ Python 3.12+ installed
- ✅ UV package manager installed
- ✅ Dependencies installed (`uv sync`)
- ✅ MCP server tested and working

**Note**: PostgreSQL database is configured but not currently required. Tools are statically registered via decorators. Database integration for dynamic tool loading will be added in a future phase.

## Add to Claude Desktop

### 1. Locate Claude Desktop Config File

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```bash
# Open the config file
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

If the file doesn't exist, create it:
```bash
mkdir -p ~/Library/Application\ Support/Claude/
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 2. Add This Configuration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-server-blueprint": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "src.mcp_server"
      ],
      "cwd": "/Users/hyalen/workspace/mcp-server-blueprint",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://hyalen@localhost:5432/mcp_server",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Note**: The `cwd` path is already set to your project directory!

### 3. Restart Claude Desktop

1. Quit Claude Desktop completely (`Cmd+Q`)
2. Reopen Claude Desktop
3. Start a new conversation

### 4. Test Your Tools

In Claude Desktop, try these prompts:

**Test Echo Tool:**
```
Use the echo tool to repeat this message: "Hello from my MCP Server!"
```

Expected result:
```json
{
  "success": true,
  "message": "Echo: Hello from my MCP Server!",
  "original_text": "Hello from my MCP Server!"
}
```

**Test Calculator Tool:**
```
Use the calculator_add tool to add 123 and 456
```

Expected result:
```json
{
  "success": true,
  "operation": "addition",
  "a": 123,
  "b": 456,
  "result": 579.0
}
```

### 5. Verify Tools Are Available

Look for the 🔧 (tools) icon in Claude Desktop. You should see:
- **echo** - Echo back the provided text
- **calculator_add** - Add two numbers together

## Alternative: Add to Cursor

If you're using Cursor instead:

### 1. Create Cursor MCP Config

Create `.cursor/mcp.json` in your project:

```json
{
  "mcp": {
    "servers": {
      "mcp-server-blueprint": {
        "command": "uv",
        "args": [
          "run",
          "python",
          "-m",
          "src.mcp_server"
        ],
        "cwd": "/Users/hyalen/workspace/mcp-server-blueprint"
      }
    }
  }
}
```

### 2. Restart Cursor

1. Quit and reopen Cursor
2. The MCP server should automatically connect

## Troubleshooting

### Tools Don't Appear

1. **Check Claude Desktop Logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Look for MCP server connection errors

2. **Verify PostgreSQL is Running:**
   ```bash
   brew services list | grep postgresql
   ```
   Should show: `postgresql@16 started`

3. **Test Server Manually:**
   ```bash
   cd /Users/hyalen/workspace/mcp-server-blueprint
   uv run python -m src.mcp_server
   ```
   Should see: "MCP tools registered: echo, calculator_add"

4. **Check Database:**
   ```bash
   /opt/homebrew/opt/postgresql@16/bin/psql mcp_server -c "SELECT name FROM tools WHERE is_active = true;"
   ```
   Should list: echo, calculator_add

### Connection Errors

If you see database connection errors:

1. **Check .env file exists:**
   ```bash
   cat .env
   ```

2. **Verify PostgreSQL is accessible:**
   ```bash
   /opt/homebrew/opt/postgresql@16/bin/psql mcp_server -c "SELECT version();"
   ```

3. **Restart PostgreSQL:**
   ```bash
   brew services restart postgresql@16
   ```

### Server Won't Start

1. **Check Python environment:**
   ```bash
   uv run python --version
   ```
   Should be Python 3.12+

2. **Reinstall dependencies:**
   ```bash
   uv sync
   ```

## Server Logs

To see detailed logs when running from Claude/Cursor:

```bash
# Run manually with debug logging
cd /Users/hyalen/workspace/mcp-server-blueprint
LOG_LEVEL=DEBUG uv run python -m src.mcp_server
```

## Next Steps

Once you've verified the tools work:
- ✅ Phase 1.1 is complete!
- Next: Phase 1.2 (HTTP Streaming) or Phase 1.3 (REST API)
- Add more tools by creating handlers in `src/core/services/tool_handlers_service.py`
- Add REST API endpoints for tool management

## Support

If you encounter issues:
1. Check logs in Claude Desktop
2. Test the server manually
3. Verify PostgreSQL is running
4. Check the `.env` file configuration

---

**Your MCP Server is ready!** 🎉

Try it in Claude Desktop and see your tools in action!

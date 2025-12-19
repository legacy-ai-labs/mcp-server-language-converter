#!/usr/bin/env python3
"""Startup script for STDIO MCP server.

This script starts the MCP server with STDIO transport,
which is used by Claude Desktop and Cursor IDE.
"""

import sys
from pathlib import Path


# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

if __name__ == "__main__":
    from src.mcp_servers.common.unified_runner import run_stdio_server

    run_stdio_server(domain="general")

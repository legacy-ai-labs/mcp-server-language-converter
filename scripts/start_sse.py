#!/usr/bin/env python3
"""Startup script for SSE (Server-Sent Events) MCP server.

This script starts the MCP server with SSE transport,
which uses Server-Sent Events for HTTP streaming.
"""

import sys
from pathlib import Path


# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

if __name__ == "__main__":
    from src.mcp_servers.common.unified_runner import run_http_server

    run_http_server(domain="general")

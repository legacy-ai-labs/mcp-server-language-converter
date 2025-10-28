#!/usr/bin/env python3
"""Startup script for Streamable HTTP MCP server.

This script starts the MCP server with Streamable HTTP transport,
which is the recommended transport for web-based deployments.
"""

import sys
from pathlib import Path


# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

if __name__ == "__main__":
    from src.mcp_servers.common.streamable_http_runner import run_streamable_http_server

    run_streamable_http_server(domain="general")

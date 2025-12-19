"""Entry point for General MCP server with unified transport support.

Usage:
    uv run python -m src.mcp_servers.mcp_general [transport]

Transport options:
    stdio           Standard input/output (default, for Claude Desktop, Cursor IDE)
    sse             Server-Sent Events on port 8000
    streamable-http Streamable HTTP on port 8002
"""

import sys

from src.mcp_servers.common.unified_runner import run_server


if __name__ == "__main__":
    # Parse transport from command line, default to stdio
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport not in ("stdio", "sse", "streamable-http"):
        print(f"Unknown transport: {transport}", file=sys.stderr)
        print("Valid options: stdio, sse, streamable-http", file=sys.stderr)
        sys.exit(1)

    run_server(domain="general", transport=transport)  # type: ignore[arg-type]

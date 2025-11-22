"""Entry point for General MCP server in STDIO mode."""

from src.mcp_servers.common.stdio_runner import run_stdio_server


if __name__ == "__main__":
    # Use decorator-based registration (Phase 2 migration)
    run_stdio_server(domain="general", use_decorators=True)

"""Entry point for COBOL Analysis MCP server in Streamable HTTP mode."""

from src.mcp_servers.common.streamable_http_runner import run_streamable_http_server


if __name__ == "__main__":
    # Use decorator-based registration (Phase 3 migration)
    run_streamable_http_server(domain="cobol_analysis", use_decorators=True)

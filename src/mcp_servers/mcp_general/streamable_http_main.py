"""Entry point for General MCP server in Streamable HTTP mode."""

from src.mcp_servers.common.streamable_http_runner import run_streamable_http_server


if __name__ == "__main__":
    run_streamable_http_server(domain="general")

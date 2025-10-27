"""Entry point for General MCP server in HTTP streaming mode."""

from src.mcp_servers.common.http_runner import run_http_server


if __name__ == "__main__":
    run_http_server(domain="general")

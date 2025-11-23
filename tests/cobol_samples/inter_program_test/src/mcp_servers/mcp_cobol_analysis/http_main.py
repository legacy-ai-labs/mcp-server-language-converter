"""Entry point for COBOL Analysis MCP server in HTTP streaming mode."""
from src.mcp_servers.common.http_runner import run_http_server


if __name__ == "__main__":
    run_http_server(domain="cobol_analysis", port=8003, use_decorators=True)

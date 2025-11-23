"""Entry point for COBOL Analysis MCP server in STDIO mode."""
from src.mcp_servers.common.stdio_runner import run_stdio_server


if __name__ == "__main__":
    run_stdio_server(domain="cobol_analysis", use_decorators=True)

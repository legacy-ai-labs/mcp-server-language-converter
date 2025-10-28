#!/usr/bin/env python3
"""Simple HTTP server that serves the test HTML file and proxies SSE requests to the MCP server.

This bypasses CORS issues by serving everything from the same origin.
"""

import http.server
import os
import socketserver
import webbrowser
from pathlib import Path

import requests  # type: ignore[import-untyped]


PORT = 8004
MCP_SERVER_URL = "http://127.0.0.1:8000"


class MCPProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/sse":
            # Proxy SSE requests to the MCP server
            self.proxy_sse_request()
        else:
            # Serve static files normally
            super().do_GET()

    def proxy_sse_request(self) -> None:
        try:
            # Forward the request to the MCP server
            url = f"{MCP_SERVER_URL}{self.path}"

            # Prepare headers for the request
            headers = {}
            for header, value in self.headers.items():
                headers[header] = value

            # Make streaming request to the MCP server
            response = requests.get(url, headers=headers, stream=True, timeout=None)  # nosec B113 - Internal proxy

            # Send response headers
            self.send_response(response.status_code)
            for header, value in response.headers.items():
                if header.lower() not in ["connection", "transfer-encoding"]:
                    self.send_header(header, value)
            self.end_headers()

            # Stream the response data
            for chunk in response.iter_content(chunk_size=512):
                if chunk:
                    self.wfile.write(chunk)
                    self.wfile.flush()

        except Exception as e:
            print(f"Proxy error: {e}")  # Debug output
            self.send_error(500, f"Proxy error: {e!s}")


def main() -> None:
    # Change to the directory containing the HTML file
    os.chdir(Path(__file__).parent)

    with socketserver.TCPServer(("", PORT), MCPProxyHandler) as httpd:
        print(f"🚀 Serving test page at http://localhost:{PORT}/test_mcp_sse.html")
        print(f"📡 Proxying SSE requests to MCP server at {MCP_SERVER_URL}")
        print("Press Ctrl+C to stop the server")

        # Open the browser automatically
        webbrowser.open(f"http://localhost:{PORT}/test_mcp_sse.html")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")


if __name__ == "__main__":
    main()

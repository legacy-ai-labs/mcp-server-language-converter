#!/usr/bin/env python3
"""Simple HTTP server that serves the test HTML file and proxies SSE requests to the MCP server.

This bypasses CORS issues by serving everything from the same origin.
"""

import http.server
import socketserver
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path


PORT = 8001
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
            req = urllib.request.Request(url)

            # Copy headers from the original request
            for header, value in self.headers.items():
                req.add_header(header, value)

            # Make the request to the MCP server
            with urllib.request.urlopen(req) as response:  # nosec B310 - Internal proxy only
                # Send response headers
                self.send_response(response.status)
                for header, value in response.headers.items():
                    if header.lower() not in ["connection", "transfer-encoding"]:
                        self.send_header(header, value)
                self.end_headers()

                # Stream the response data
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()

        except Exception as e:
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
    import os

    main()

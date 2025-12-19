#!/usr/bin/env python3
"""Start all MCP servers (SSE and Streamable HTTP).

This script starts both the SSE and Streamable HTTP servers for testing.
"""

import logging
import os
import subprocess  # nosec B404 - Required for process management
import sys
import time
from typing import Any


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def start_server(module_name: str, server_name: str, transport: str = "") -> subprocess.Popen[Any]:
    """Start a server process."""
    logger.info(f"Starting {server_name}...")

    cmd = [sys.executable, "-m", module_name]
    if transport:
        cmd.append(transport)

    try:
        process = subprocess.Popen(  # nosec B603 - Safe command execution
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Give the server a moment to start
        time.sleep(2)

        if process.poll() is None:
            logger.info(f"✅ {server_name} started successfully (PID: {process.pid})")
            return process
        else:
            logger.error(f"❌ {server_name} failed to start")
            raise RuntimeError(f"Failed to start {server_name}")

    except Exception as e:
        logger.error(f"❌ Failed to start {server_name}: {e}")
        raise


def main() -> None:
    """Start all servers."""
    logger.info("🚀 Starting MCP Servers")
    logger.info("=" * 50)

    # Start SSE server
    sse_process = start_server(
        "src.mcp_servers.mcp_general", "SSE Server (Port 8000)", transport="sse"
    )

    if not sse_process:
        logger.error("Failed to start SSE server. Exiting.")
        return

    # Start Streamable HTTP server on a different port
    # We need to modify the config or use environment variables
    os.environ["STREAMABLE_HTTP_PORT"] = "8002"

    streamable_process = start_server(
        "src.mcp_servers.mcp_general",
        "Streamable HTTP Server (Port 8002)",
        transport="streamable-http",
    )

    if not streamable_process:
        logger.error("Failed to start Streamable HTTP server. Exiting.")
        sse_process.terminate()
        return

    logger.info("")
    logger.info("🎉 Both servers are running!")
    logger.info("")
    logger.info("Test URLs:")
    logger.info("  SSE: http://127.0.0.1:8000/sse")
    logger.info("  Streamable HTTP: http://127.0.0.1:8002/mcp")
    logger.info("")
    logger.info("Test commands:")
    logger.info("  uv run python test_both_transports.py")
    logger.info("")
    logger.info("Press Ctrl+C to stop all servers")

    try:
        # Wait for both processes
        while True:
            time.sleep(1)

            # Check if either process died
            if sse_process.poll() is not None:
                logger.error("SSE server died unexpectedly")
                break

            if streamable_process.poll() is not None:
                logger.error("Streamable HTTP server died unexpectedly")
                break

    except KeyboardInterrupt:
        logger.info("")
        logger.info("🛑 Shutting down servers...")

        # Terminate both processes
        if sse_process.poll() is None:
            sse_process.terminate()
            logger.info("SSE server terminated")

        if streamable_process.poll() is None:
            streamable_process.terminate()
            logger.info("Streamable HTTP server terminated")

        logger.info("👋 All servers stopped")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Startup script for HTTP streaming MCP server."""

import asyncio
import logging
import sys
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.mcp_servers.mcp_general.http_server import main


def setup_logging() -> None:
    """Configure logging for HTTP streaming server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting HTTP streaming MCP server...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("HTTP streaming server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start HTTP streaming server: {e}", exc_info=True)
        sys.exit(1)

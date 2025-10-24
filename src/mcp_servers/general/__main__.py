"""Entry point for MCP server in STDIO mode."""

import asyncio
import logging
import sys
import traceback

from src.mcp_servers.general.dynamic_tools import load_tools_from_database
from src.mcp_servers.general.external_tools import ExternalToolsLoader
from src.mcp_servers.general.server import mcp


# Configure logging to stderr so Claude Desktop can see it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Important: log to stderr for Claude Desktop
)

logger = logging.getLogger(__name__)


async def startup() -> None:
    """Initialize database and load tools."""
    try:
        # Load internal tools from database
        await load_tools_from_database()
        logger.info("Internal tools loaded successfully from database")

        # Load external tools from external MCP servers
        external_loader = ExternalToolsLoader()
        await external_loader.load_external_tools()
        logger.info("External tools loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load tools: {e}")
        raise


def main() -> None:
    """Main entry point for MCP server."""
    try:
        # Log startup to stderr for Claude Desktop
        print("MCP Server starting...", file=sys.stderr)
        logger.info("Running MCP server with STDIO transport...")

        # Initialize database and load tools
        asyncio.run(startup())

        # Run MCP server with STDIO transport
        # Tools are now loaded dynamically from database
        mcp.run(transport="stdio")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        print("MCP Server shutting down (KeyboardInterrupt)", file=sys.stderr)
    except Exception as e:
        # Log to stderr so Claude Desktop can see the error
        error_msg = f"Server error: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Entry point for MCP server in STDIO mode."""

import logging
import sys

# Import tools to ensure @mcp.tool() decorators are registered
import src.mcp_servers.general.tools  # noqa: F401
from src.mcp_servers.general.server import mcp


# Configure logging to stderr so Claude Desktop can see it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Important: log to stderr for Claude Desktop
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for MCP server."""
    try:
        # Log startup to stderr for Claude Desktop
        print("MCP Server starting...", file=sys.stderr)
        logger.info("Running MCP server with STDIO transport...")

        # Run MCP server with STDIO transport
        # Tools are registered via @mcp.tool() decorators in tools module
        mcp.run(transport="stdio")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        print("MCP Server shutting down (KeyboardInterrupt)", file=sys.stderr)
    except Exception as e:
        # Log to stderr so Claude Desktop can see the error
        error_msg = f"Server error: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

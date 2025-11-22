#!/usr/bin/env python3
"""Demo script for HTTP streaming MCP server."""

import logging
import sys
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config import get_settings


def setup_logging() -> None:
    """Configure logging for demo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def print_banner() -> None:
    """Print demo banner."""
    print("=" * 60)
    print("🚀 MCP Server Language Converter - HTTP Streaming Demo")
    print("=" * 60)
    print()


def print_usage() -> None:
    """Print usage instructions."""
    settings = get_settings()

    print("📋 HTTP Streaming Server Usage:")
    print()
    print("1. Start the HTTP streaming server:")
    print("   uv run python -m src.mcp_servers.mcp_general.http_main")
    print()
    print(f"   Server will be available at: http://{settings.http_host}:{settings.http_port}")
    print()
    print("2. Test with curl:")
    print("   curl -N -H 'Accept: text/event-stream' \\")
    print("        -H 'Cache-Control: no-cache' \\")
    print(f"        http://{settings.http_host}:{settings.http_port}/sse")
    print()
    print("3. Test with HTTPie:")
    print(f"   http --stream GET {settings.http_host}:{settings.http_port}/sse")
    print()
    print("4. Available tools:")
    print("   - echo: Echo back provided text")
    print("   - calculator_add: Add two numbers together")
    print()
    print("5. Example JavaScript client:")
    print(
        """
   const eventSource = new EventSource('http://localhost:8000/sse');
   eventSource.onmessage = function(event) {
       const data = JSON.parse(event.data);
       console.log('MCP response:', data);
   };
   """
    )
    print()


def print_configuration() -> None:
    """Print current configuration."""
    settings = get_settings()

    print("⚙️  Current Configuration:")
    print(f"   HTTP Host: {settings.http_host}")
    print(f"   HTTP Port: {settings.http_port}")
    print(f"   HTTP Streaming Enabled: {settings.http_streaming_enabled}")
    print(f"   Database URL: {settings.database_url}")
    print(f"   Log Level: {settings.log_level}")
    print()


def print_next_steps() -> None:
    """Print next steps."""
    print("🎯 Next Steps:")
    print()
    print("1. Initialize the database:")
    print("   uv run python scripts/init_db.py")
    print()
    print("2. Seed initial tools:")
    print("   uv run python scripts/seed_tools.py")
    print()
    print("3. Start the HTTP streaming server:")
    print("   uv run python -m src.mcp_servers.general.http_main")
    print()
    print("4. Test the connection:")
    print("   curl -N -H 'Accept: text/event-stream' http://localhost:8000/sse")
    print()
    print("📚 Documentation:")
    print("   - HTTP Streaming Guide: docs/HTTP_STREAMING.md")
    print("   - Usage Guide: docs/USAGE.md")
    print("   - Architecture: docs/ARCHITECTURE.md")
    print()


def main() -> None:
    """Main demo function."""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        print_banner()
        print_configuration()
        print_usage()
        print_next_steps()

        logger.info("HTTP streaming demo completed successfully")

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

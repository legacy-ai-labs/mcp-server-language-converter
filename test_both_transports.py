#!/usr/bin/env python3
"""Test both SSE and Streamable HTTP transports.

This script demonstrates how to use both transport types with our MCP server.
"""

import asyncio
import logging

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sse_transport() -> None:
    """Test the SSE transport."""
    logger.info("=" * 60)
    logger.info("TESTING SSE TRANSPORT")
    logger.info("=" * 60)

    url = "http://127.0.0.1:8000/sse"

    try:
        async with sse_client(url) as (read_stream, write_stream), ClientSession(
            read_stream, write_stream
        ) as session:
            logger.info("✅ Connected to SSE MCP server!")

            # Initialize
            init_result = await session.initialize()
            logger.info(f"Initialization: {init_result.serverInfo.name}")

            # List tools
            tools_result = await session.list_tools()
            logger.info(f"Available tools: {[tool.name for tool in tools_result.tools]}")

            # Test echo tool
            if any(tool.name == "echo" for tool in tools_result.tools):
                call_result = await session.call_tool("echo", {"text": "Hello SSE!"})
                logger.info(f"Echo result: {call_result.content[0].text}")

            logger.info("✅ SSE transport test completed successfully!")

    except Exception as e:
        logger.error(f"❌ SSE transport test failed: {e}")


async def test_streamable_http_transport() -> None:
    """Test the Streamable HTTP transport."""
    logger.info("=" * 60)
    logger.info("TESTING STREAMABLE HTTP TRANSPORT")
    logger.info("=" * 60)

    url = "http://127.0.0.1:8002/mcp"

    try:
        async with streamablehttp_client(url) as (
            read_stream,
            write_stream,
            get_session_id,
        ), ClientSession(read_stream, write_stream) as session:
            logger.info("✅ Connected to Streamable HTTP MCP server!")

            # Get session ID
            session_id = get_session_id()
            logger.info(f"Session ID: {session_id}")

            # Initialize
            init_result = await session.initialize()
            logger.info(f"Initialization: {init_result.serverInfo.name}")

            # List tools
            tools_result = await session.list_tools()
            logger.info(f"Available tools: {[tool.name for tool in tools_result.tools]}")

            # Test echo tool
            if any(tool.name == "echo" for tool in tools_result.tools):
                call_result = await session.call_tool("echo", {"text": "Hello Streamable HTTP!"})
                logger.info(f"Echo result: {call_result.content[0].text}")

            # Test calculator tool
            if any(tool.name == "calculator_add" for tool in tools_result.tools):
                call_result = await session.call_tool("calculator_add", {"a": 10, "b": 5})
                logger.info(f"Calculator result: {call_result.content[0].text}")

            logger.info("✅ Streamable HTTP transport test completed successfully!")

    except Exception as e:
        logger.error(f"❌ Streamable HTTP transport test failed: {e}")


async def main() -> None:
    """Run all transport tests."""
    logger.info("🚀 Starting MCP Transport Tests")
    logger.info("Make sure both servers are running:")
    logger.info("  SSE: uv run python -m src.mcp_servers.mcp_general.http_main")
    logger.info(
        "  Streamable HTTP: uv run python -m src.mcp_servers.mcp_general.streamable_http_main"
    )
    logger.info("")

    # Test SSE transport
    await test_sse_transport()

    logger.info("")

    # Test Streamable HTTP transport
    await test_streamable_http_transport()

    logger.info("")
    logger.info("🎉 All transport tests completed!")


if __name__ == "__main__":
    asyncio.run(main())

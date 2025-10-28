#!/usr/bin/env python3
"""Test client for Streamable HTTP MCP server.

This demonstrates how to properly connect to a Streamable HTTP MCP server
using the official MCP client library.
"""

import asyncio
import logging

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_streamable_http() -> None:
    """Test the Streamable HTTP MCP server."""
    url = "http://127.0.0.1:8002/mcp"

    logger.info(f"Connecting to Streamable HTTP MCP server at {url}")

    try:
        async with streamablehttp_client(url) as (
            read_stream,
            write_stream,
            get_session_id,
        ), ClientSession(read_stream, write_stream) as session:
            logger.info("Connected to MCP server!")

            # Get session ID
            session_id = get_session_id()
            logger.info(f"Session ID: {session_id}")

            # Initialize the session
            logger.info("Initializing session...")
            init_result = await session.initialize()
            logger.info(f"Initialization result: {init_result}")

            # List available tools
            logger.info("Listing available tools...")
            tools_result = await session.list_tools()
            logger.info(f"Available tools: {tools_result}")

            # Test the echo tool
            if tools_result.tools:
                echo_tool = next((tool for tool in tools_result.tools if tool.name == "echo"), None)
                if echo_tool:
                    logger.info("Testing echo tool...")
                    call_result = await session.call_tool(
                        "echo", {"text": "Hello from Streamable HTTP!"}
                    )
                    logger.info(f"Echo result: {call_result}")
                else:
                    logger.warning("Echo tool not found")

            # Test the calculator tool
            calc_tool = next(
                (tool for tool in tools_result.tools if tool.name == "calculator_add"), None
            )
            if calc_tool:
                logger.info("Testing calculator tool...")
                call_result = await session.call_tool("calculator_add", {"a": 5, "b": 3})
                logger.info(f"Calculator result: {call_result}")
            else:
                logger.warning("Calculator tool not found")

            logger.info("Test completed successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_streamable_http())

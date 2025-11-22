#!/usr/bin/env python3
"""Test script for Streamable HTTP MCP server - COBOL Analysis domain.

This script tests the streamable HTTP transport for the mcp_cobol_analysis server.
It uses the official MCP client library to properly handle session management.
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent


# Sample COBOL code for testing
SAMPLE_COBOL = """IDENTIFICATION DIVISION.
PROGRAM-ID. ACCOUNTVALIDATOR.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-VALIDATION-RESULT   PIC X(1).
    88 VALID-ACCOUNT      VALUE 'Y'.
    88 INVALID-ACCOUNT    VALUE 'N'.

PROCEDURE DIVISION.
VALIDATE-ACCOUNT-MAIN.
    MOVE 'Y' TO WS-VALIDATION-RESULT.
    IF WS-VALIDATION-RESULT = 'Y'
        DISPLAY 'Valid account'
    ELSE
        DISPLAY 'Invalid account'
    END-IF.
    STOP RUN.
"""


def _get_text_content(content: Any) -> str | None:
    """Extract text from MCP content, handling type checking."""
    if isinstance(content, TextContent):
        text: str = content.text
        return text
    return None


def _print_result(result_text: str) -> None:
    """Print formatted result from tool execution."""
    try:
        result_data = json.loads(result_text)
        if result_data.get("success"):
            print(f"   Success: {result_data.get('success')}")
            if "ast" in result_data:
                print("   AST structure generated")
            if "metadata" in result_data:
                metadata = result_data["metadata"]
                print(f"   Program ID: {metadata.get('program_id', 'N/A')}")
                print(f"   Sections: {metadata.get('section_count', 0)}")
        else:
            print(f"   ⚠️  Tool returned error: {result_data.get('error', 'Unknown')}")
    except json.JSONDecodeError:
        print(f"   Response: {result_text[:200]}...")


async def _test_initialize(session: ClientSession) -> bool:
    """Test session initialization."""
    print("Step 1: Initializing session...")
    try:
        init_result = await session.initialize()
        print(f"✅ Connected to: {init_result.serverInfo.name}")
        print(f"   Version: {init_result.serverInfo.version}")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False


async def _test_list_tools(session: ClientSession) -> bool:
    """Test listing available tools."""
    print("Step 2: Listing available tools...")
    try:
        tools_result = await session.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]
        print(f"✅ Found {len(tool_names)} tools:")
        for tool_name in tool_names:
            print(f"   - {tool_name}")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to list tools: {e}")
        return False


async def _test_parse_cobol(session: ClientSession) -> bool:
    """Test parse_cobol tool."""
    print("Step 3: Testing parse_cobol tool...")
    try:
        result = await session.call_tool("parse_cobol", {"source_code": SAMPLE_COBOL})
        if result.content and len(result.content) > 0:
            print("✅ parse_cobol executed successfully")
            text_content = _get_text_content(result.content[0])
            if text_content:
                _print_result(text_content)
            else:
                print("   ⚠️  Non-text content received")
        else:
            print("⚠️  No content in response")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to call parse_cobol: {e}")
        traceback.print_exc()
        return False


async def _test_parse_cobol_raw(session: ClientSession) -> bool:
    """Test parse_cobol_raw tool."""
    print("Step 4: Testing parse_cobol_raw tool...")
    try:
        result = await session.call_tool("parse_cobol_raw", {"source_code": SAMPLE_COBOL})
        if result.content and len(result.content) > 0:
            print("✅ parse_cobol_raw executed successfully")
            text_content = _get_text_content(result.content[0])
            if text_content:
                try:
                    result_data = json.loads(text_content)
                    if result_data.get("success"):
                        print("   Raw parse tree generated")
                    else:
                        print(f"   ⚠️  Tool returned error: {result_data.get('error', 'Unknown')}")
                except json.JSONDecodeError:
                    print(f"   Response: {text_content[:200]}...")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to call parse_cobol_raw: {e}")
        return False


async def _test_parse_cobol_file(session: ClientSession) -> None:
    """Test parse_cobol with file path."""
    print("Step 5: Testing parse_cobol with file path...")
    sample_file = Path("tests/cobol_samples/ACCOUNT-VALIDATOR-SIMPLE.cbl")
    if sample_file.exists():
        try:
            result = await session.call_tool("parse_cobol", {"file_path": str(sample_file)})
            if result.content and len(result.content) > 0:
                print("✅ parse_cobol with file_path executed successfully")
                text_content = _get_text_content(result.content[0])
                if text_content:
                    try:
                        result_data = json.loads(text_content)
                        if result_data.get("success"):
                            print("   File parsed successfully")
                    except json.JSONDecodeError:
                        pass
            print()
        except Exception as e:
            print(f"⚠️  Failed to call parse_cobol with file_path: {e}")
            print()
    else:
        print(f"⚠️  Sample file not found: {sample_file}")
        print("   Skipping file path test\n")


async def test_streamable_http_cobol_analysis() -> bool:
    """Test the streamable HTTP MCP server for COBOL analysis."""
    url = "http://127.0.0.1:8002/mcp"

    print("=" * 70)
    print("Testing Streamable HTTP MCP Server - COBOL Analysis Domain")
    print("=" * 70)
    print(f"Connecting to: {url}\n")

    try:
        async with streamablehttp_client(url) as (
            read_stream,
            write_stream,
            _,
        ), ClientSession(read_stream, write_stream) as session:
            if not await _test_initialize(session):
                return False
            if not await _test_list_tools(session):
                return False
            if not await _test_parse_cobol(session):
                return False
            if not await _test_parse_cobol_raw(session):
                return False
            await _test_parse_cobol_file(session)

            print("=" * 70)
            print("✅ All tests completed successfully!")
            print("=" * 70)
            return True

    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        print(
            "   Start it with: uv run python -m src.mcp_servers.mcp_cobol_analysis.streamable_http_main"
        )
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_streamable_http_cobol_analysis())
    sys.exit(0 if success else 1)

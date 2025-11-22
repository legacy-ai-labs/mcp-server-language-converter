#!/usr/bin/env python3
"""Integration test for observability middleware.

This script tests that the ObservabilityMiddleware is working correctly by:
1. Creating a test MCP server with observability
2. Registering a test tool
3. Simulating a tool call
4. Verifying data was recorded in the database
"""

import asyncio
import sys
from typing import Any

from fastmcp import FastMCP

from src.core.config import get_settings
from src.core.database import async_session_factory
from src.core.repositories.tool_execution_repository import ToolExecutionRepository
from src.mcp_servers.common.observability_middleware import ObservabilityMiddleware


settings = get_settings()


async def test_observability() -> None:
    """Test observability middleware integration."""
    print("=" * 60)
    print("Testing Observability Middleware")
    print("=" * 60)
    print()

    # Step 1: Create server with observability middleware
    print("1. Creating MCP server with ObservabilityMiddleware...")
    mcp = FastMCP(name="Test Server", version="1.0.0")

    # Add observability middleware
    obs_middleware = ObservabilityMiddleware(domain="test", transport="stdio")
    mcp.add_middleware(obs_middleware)
    print("   ✓ Middleware added")
    print()

    # Step 2: Register a test tool
    print("2. Registering test tool...")

    # Define the function first, then decorate it
    async def test_echo_impl(message: str) -> dict[str, Any]:
        """Echo back the message (test tool)."""
        return {"success": True, "message": message, "echoed": True}

    # Register it as a tool (decorator registers it, we don't need the return value)
    mcp.tool()(test_echo_impl)

    print("   ✓ Test tool 'test_echo' registered")
    print()

    # Step 3: Get execution count before test
    print("3. Checking database before test...")
    async with async_session_factory() as session:
        repo = ToolExecutionRepository(session)
        # Count executions for our test tool
        # Note: We'll check total count since this is a new tool
        initial_count = len(await repo.get_recent_by_tool("test_echo", limit=1000))
        print(f"   Initial 'test_echo' execution count: {initial_count}")
    print()

    # Step 4: Simulate tool call
    print("4. Simulating tool call...")
    print("   Calling: test_echo(message='Hello, Observability!')")

    # We can't easily call the tool through FastMCP programmatically,
    # so we'll test the middleware directly
    from types import SimpleNamespace

    # Create a mock context that looks like FastMCP's MiddlewareContext
    mock_message = SimpleNamespace(name="test_echo", arguments={"message": "Hello, Observability!"})

    mock_context = SimpleNamespace(
        message=mock_message,
        fastmcp_context=None,  # No session context in this test
    )

    # Mock call_next that simulates tool execution
    async def mock_call_next(_ctx: object) -> object:
        """Mock the next handler in middleware chain."""
        # Simulate tool execution using the underlying function
        result = await test_echo_impl(message="Hello, Observability!")
        # Return a mock result with content attribute
        return SimpleNamespace(content=result)

    # Execute through middleware
    try:
        result = await obs_middleware.on_call_tool(mock_context, mock_call_next)
        print("   ✓ Tool executed successfully")
        print(f"   Result: {result.content}")
    except Exception as e:
        print(f"   ✗ Tool execution failed: {e}")
        sys.exit(1)
    print()

    # Step 5: Wait a moment for async database persistence
    print("5. Waiting for database persistence (2 seconds)...")
    await asyncio.sleep(2)
    print("   ✓ Wait complete")
    print()

    # Step 6: Verify data was recorded
    print("6. Verifying data in database...")
    async with async_session_factory() as session:
        repo = ToolExecutionRepository(session)

        # Get recent executions for our test tool
        executions = await repo.get_recent_by_tool("test_echo", limit=10)
        final_count = len(executions)

        print(f"   Final 'test_echo' execution count: {final_count}")

        if final_count > initial_count:
            new_records = final_count - initial_count
            print(f"   ✓ {new_records} new execution record(s) created!")
            print()

            # Show the most recent execution details
            if executions:
                latest = executions[0]
                print("   Latest execution details:")
                print(f"   - Tool: {latest.tool_name}")
                print(f"   - Status: {latest.status}")
                print(f"   - Duration: {latest.duration_ms:.2f}ms")
                print(f"   - Domain: {latest.domain}")
                print(f"   - Transport: {latest.transport}")
                print(f"   - Correlation ID: {latest.correlation_id}")
                print(f"   - Started at: {latest.started_at}")

                # Check if input/output logging is enabled
                if settings.log_tool_inputs and latest.input_params:
                    print(f"   - Input params: {latest.input_params}")
                if settings.log_tool_outputs and latest.output_data:
                    print(f"   - Output data: {latest.output_data}")
        else:
            print("   ✗ No new execution records found!")
            print("   This might indicate:")
            print("   - Database persistence is disabled (check enable_execution_logging)")
            print("   - Event loop mismatch (check logs for warnings)")
            print("   - Database connection issues")
            sys.exit(1)

    print()
    print("=" * 60)
    print("✓ Observability Middleware Test PASSED")
    print("=" * 60)
    print()
    print("Configuration used:")
    print(f"  - enable_metrics: {settings.enable_metrics}")
    print(f"  - enable_execution_logging: {settings.enable_execution_logging}")
    print(f"  - log_tool_inputs: {settings.log_tool_inputs}")
    print(f"  - log_tool_outputs: {settings.log_tool_outputs}")
    print()


if __name__ == "__main__":
    asyncio.run(test_observability())

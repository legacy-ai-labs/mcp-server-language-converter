"""Prometheus metrics instrumentation for MCP tools.

This module provides Prometheus-compatible metrics collection for:
- Request counts and rates
- Latency percentiles (p50, p95, p99)
- Error rates and types
- In-progress requests

Metrics are exposed at /metrics endpoint in Prometheus exposition format.
"""

from prometheus_client import Counter, Gauge, Histogram, Info


# Tool call metrics with labels for filtering
tool_calls_total = Counter(
    "mcp_tool_calls_total",
    "Total number of tool calls",
    ["tool_name", "domain", "transport", "status"],
)

# Request/response size metrics
request_size_bytes = Histogram(
    "mcp_request_size_bytes",
    "Size of tool input parameters in bytes",
    ["tool_name", "domain", "transport"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
)

response_size_bytes = Histogram(
    "mcp_response_size_bytes",
    "Size of tool output in bytes",
    ["tool_name", "domain", "transport"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
)

tool_errors_total = Counter(
    "mcp_tool_errors_total",
    "Total number of tool errors by type",
    ["tool_name", "domain", "transport", "error_type"],
)

# Histogram automatically calculates percentiles (p50, p95, p99)
# Buckets are optimized for typical tool execution times
tool_duration_seconds = Histogram(
    "mcp_tool_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_name", "domain", "transport"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0],
)

# Gauge for tracking concurrent executions
tool_in_progress = Gauge(
    "mcp_tool_in_progress",
    "Number of tool executions currently in progress",
    ["tool_name", "domain", "transport"],
)

# Server information (set once at startup)
server_info = Info("mcp_server", "MCP server information")


class PrometheusMetrics:
    """Prometheus metrics recorder for MCP tool executions.

    This class provides a simple interface to record metrics that are
    automatically exposed via the Prometheus client library.

    Usage:
        PROMETHEUS_METRICS.record_tool_call(
            tool_name="divide",
            domain="general",
            transport="stdio",
            status="success",
            duration_seconds=0.123,
        )
    """

    @staticmethod
    def record_tool_call(
        tool_name: str,
        domain: str,
        transport: str,
        status: str,
        duration_seconds: float,
        error_type: str | None = None,
    ) -> None:
        """Record a completed tool execution.

        Args:
            tool_name: Name of the tool that was executed
            domain: Domain the tool belongs to (general, kubernetes, etc.)
            transport: Transport protocol used (stdio, http, rest)
            status: Execution status (success, error, timeout)
            duration_seconds: Execution duration in seconds
            error_type: Type of error if status is error (e.g., ValueError, TimeoutError)
        """
        # Increment counter for total calls
        tool_calls_total.labels(
            tool_name=tool_name,
            domain=domain,
            transport=transport,
            status=status,
        ).inc()

        # Record duration in histogram (automatically calculates percentiles)
        tool_duration_seconds.labels(
            tool_name=tool_name,
            domain=domain,
            transport=transport,
        ).observe(duration_seconds)

        # Record error if applicable
        if status == "error" and error_type:
            tool_errors_total.labels(
                tool_name=tool_name,
                domain=domain,
                transport=transport,
                error_type=error_type,
            ).inc()

    @staticmethod
    def start_tool_execution(tool_name: str, domain: str, transport: str) -> None:
        """Mark a tool execution as started (increment in-progress gauge).

        Args:
            tool_name: Name of the tool
            domain: Domain the tool belongs to
            transport: Transport protocol used
        """
        tool_in_progress.labels(
            tool_name=tool_name,
            domain=domain,
            transport=transport,
        ).inc()

    @staticmethod
    def end_tool_execution(tool_name: str, domain: str, transport: str) -> None:
        """Mark a tool execution as ended (decrement in-progress gauge).

        Args:
            tool_name: Name of the tool
            domain: Domain the tool belongs to
            transport: Transport protocol used
        """
        tool_in_progress.labels(
            tool_name=tool_name,
            domain=domain,
            transport=transport,
        ).dec()

    @staticmethod
    def set_server_info(version: str, python_version: str, environment: str = "production") -> None:
        """Set server metadata information (call once at startup).

        Args:
            version: Server version
            python_version: Python version
            environment: Environment name (production, staging, development)
        """
        server_info.info(
            {
                "version": version,
                "python_version": python_version,
                "environment": environment,
            }
        )

    @staticmethod
    def record_request_size(
        tool_name: str,
        domain: str,
        transport: str,
        size_bytes: int,
    ) -> None:
        """Record the size of a tool request (input parameters).

        Args:
            tool_name: Name of the tool
            domain: Domain the tool belongs to
            transport: Transport protocol used
            size_bytes: Size of the request in bytes
        """
        request_size_bytes.labels(
            tool_name=tool_name,
            domain=domain,
            transport=transport,
        ).observe(size_bytes)

    @staticmethod
    def record_response_size(
        tool_name: str,
        domain: str,
        transport: str,
        size_bytes: int,
    ) -> None:
        """Record the size of a tool response (output data).

        Args:
            tool_name: Name of the tool
            domain: Domain the tool belongs to
            transport: Transport protocol used
            size_bytes: Size of the response in bytes
        """
        response_size_bytes.labels(
            tool_name=tool_name,
            domain=domain,
            transport=transport,
        ).observe(size_bytes)


# Singleton instance for easy access
PROMETHEUS_METRICS = PrometheusMetrics()

# =============================================================================
# MCP Server Docker Image
# Multi-stage build for production-ready deployment
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with UV
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

# Set UV environment variables for optimal builds
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12

WORKDIR /app

# Copy dependency files first (leverages Docker layer caching)
# README.md is required by hatchling build backend for package metadata
COPY pyproject.toml uv.lock README.md ./

# Install dependencies into virtual environment
# Using cache mount for faster rebuilds
# --no-install-project skips installing the local project, only installs dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Metadata
LABEL maintainer="MCP Server Team" \
      description="MCP Server with SSE and Streamable HTTP transports" \
      version="1.0.0"

# Security: Create non-root user before any file operations
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid mcp --shell /bin/bash --create-home mcp

# Install runtime dependencies only (minimal footprint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    supervisor \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY --chown=mcp:mcp src/ ./src/
COPY --chown=mcp:mcp config/ ./config/
COPY --chown=mcp:mcp migrations/ ./migrations/
COPY --chown=mcp:mcp alembic.ini ./

# Remove macOS AppleDouble files (._*) that may have slipped through
RUN find /app -name "._*" -type f -delete 2>/dev/null || true

# Copy required scripts
COPY --chown=mcp:mcp scripts/init_db.py ./scripts/
COPY --chown=mcp:mcp scripts/start_metrics_server.py ./scripts/

# Copy Docker-specific configuration files
COPY --chown=mcp:mcp docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY --chown=mcp:mcp docker/entrypoint.sh /entrypoint.sh

# Ensure entrypoint is executable
RUN chmod +x /entrypoint.sh

# Create directories for supervisor
RUN mkdir -p /tmp && chown mcp:mcp /tmp

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Security: Disable pip cache and version check
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Application configuration defaults
ENV DATABASE_URL="postgresql+asyncpg://mcp:mcp@postgres:5432/mcp_server" \
    DATABASE_ECHO="false" \
    ENVIRONMENT="production" \
    LOG_LEVEL="INFO" \
    HTTP_HOST="0.0.0.0" \
    HTTP_PORT="8000" \
    STREAMABLE_HTTP_HOST="0.0.0.0" \
    STREAMABLE_HTTP_PORT="8002" \
    ENABLE_METRICS="true" \
    ENABLE_EXECUTION_LOGGING="true" \
    METRICS_PORT="9090" \
    LOG_TOOL_INPUTS="false" \
    LOG_TOOL_OUTPUTS="false"

# Expose ports for all services
# 8000 - SSE transport (general domain)
# 8001 - SSE transport (cobol_analysis domain)
# 8002 - Streamable HTTP transport (general domain)
# 8003 - Streamable HTTP transport (cobol_analysis domain)
# 9090 - Prometheus metrics and health check
EXPOSE 8000 8001 8002 8003 9090

# Health check using the metrics server's health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# Switch to non-root user for security
USER mcp

# Entrypoint handles database initialization and migrations
ENTRYPOINT ["/entrypoint.sh"]

# Default command runs supervisord to manage all server processes
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

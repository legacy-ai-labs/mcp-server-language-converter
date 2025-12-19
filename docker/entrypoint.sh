#!/bin/bash
# =============================================================================
# MCP Server Container Entrypoint
# Handles database readiness, migrations, and server startup
# =============================================================================
set -e

echo "=========================================="
echo "MCP Server Container Starting"
echo "Environment: ${ENVIRONMENT:-production}"
echo "=========================================="

# -----------------------------------------------------------------------------
# Function: Wait for PostgreSQL to be ready
# -----------------------------------------------------------------------------
wait_for_postgres() {
    local max_attempts="${1:-30}"
    local attempt=1

    # Extract host and port from DATABASE_URL
    # Format: postgresql+asyncpg://user:pass@host:port/db
    local db_host
    local db_port

    db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    # Default values if parsing fails
    db_host="${db_host:-postgres}"
    db_port="${db_port:-5432}"

    echo "Waiting for PostgreSQL at ${db_host}:${db_port}..."

    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h "$db_host" -p "$db_port" > /dev/null 2>&1; then
            echo "PostgreSQL is ready!"
            return 0
        fi

        echo "Attempt $attempt/$max_attempts: PostgreSQL not ready, waiting 2s..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "ERROR: PostgreSQL did not become ready after $max_attempts attempts"
    return 1
}

# -----------------------------------------------------------------------------
# Function: Run database migrations
# -----------------------------------------------------------------------------
run_migrations() {
    echo "Running database migrations..."

    if alembic upgrade head; then
        echo "Migrations completed successfully!"
        return 0
    else
        echo "ERROR: Migration failed!"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Function: Verify database connection
# -----------------------------------------------------------------------------
verify_database() {
    echo "Verifying database connection..."

    python -c "
import asyncio
from sqlalchemy import text

async def check():
    from src.core.database import engine
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))
        print('Database connection verified!')

asyncio.run(check())
" || {
        echo "ERROR: Database connection verification failed!"
        return 1
    }
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------

# Wait for database to be ready
if ! wait_for_postgres 30; then
    echo "Failed to connect to PostgreSQL. Exiting."
    exit 1
fi

# Run database migrations
if ! run_migrations; then
    echo "Migration failed. Exiting."
    exit 1
fi

# Verify database connection
if ! verify_database; then
    echo "Database verification failed. Exiting."
    exit 1
fi

echo "=========================================="
echo "Database ready. Starting MCP servers..."
echo "Ports:"
echo "  - SSE General:        8000"
echo "  - SSE COBOL:          8001"
echo "  - Streamable General: 8002"
echo "  - Streamable COBOL:   8003"
echo "  - Metrics:            9090"
echo "=========================================="

# Execute the main command (supervisord)
# Using exec ensures signals are forwarded properly
exec "$@"

#!/usr/bin/env bash
# Test script to verify observability middleware is working correctly

set -e

echo "========================================="
echo "Observability Middleware Testing Script"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1: Check database connection${NC}"
if psql -lqt -U postgres 2>/dev/null | cut -d \| -f 1 | grep -qw mcp_server; then
    echo -e "${GREEN}✓ Database 'mcp_server' exists${NC}"
else
    echo -e "${YELLOW}⚠ Database 'mcp_server' not found. Creating...${NC}"
    createdb -U postgres mcp_server || echo "Database might already exist or permissions issue"
fi

echo ""
echo -e "${BLUE}Step 2: Initialize database schema${NC}"
uv run python scripts/init_db.py
echo -e "${GREEN}✓ Database initialized${NC}"

echo ""
echo -e "${BLUE}Step 3: Seed tools${NC}"
uv run python scripts/seed_tools.py
echo -e "${GREEN}✓ Tools seeded${NC}"

echo ""
echo -e "${BLUE}Step 4: Check current execution count${NC}"
BEFORE_COUNT=$(./scripts/db.sh query "SELECT COUNT(*) FROM tool_executions;" 2>/dev/null | tail -1 | tr -d ' ')
echo "Current executions in database: $BEFORE_COUNT"

echo ""
echo -e "${BLUE}Step 5: Test observability with a sample tool call${NC}"
echo "Running test_observability_integration.py..."
uv run python scripts/test_observability_integration.py

echo ""
echo -e "${BLUE}Step 6: Verify data was recorded${NC}"
AFTER_COUNT=$(./scripts/db.sh query "SELECT COUNT(*) FROM tool_executions;" 2>/dev/null | tail -1 | tr -d ' ')
echo "Executions after test: $AFTER_COUNT"

if [ "$AFTER_COUNT" -gt "$BEFORE_COUNT" ]; then
    echo -e "${GREEN}✓ New execution records created!${NC}"
    DIFF=$((AFTER_COUNT - BEFORE_COUNT))
    echo "  Added $DIFF new record(s)"
else
    echo -e "${YELLOW}⚠ No new execution records (might indicate an issue)${NC}"
fi

echo ""
echo -e "${BLUE}Step 7: Show recent executions${NC}"
./scripts/db.sh query "
SELECT
    tool_name,
    status,
    ROUND(duration_ms::numeric, 2) as duration_ms,
    transport,
    domain,
    started_at
FROM tool_executions
ORDER BY started_at DESC
LIMIT 5;
"

echo ""
echo -e "${BLUE}Step 8: Show execution statistics${NC}"
./scripts/db.sh query "
SELECT
    tool_name,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successes,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as errors,
    ROUND(AVG(duration_ms)::numeric, 2) as avg_duration_ms,
    ROUND(MIN(duration_ms)::numeric, 2) as min_duration_ms,
    ROUND(MAX(duration_ms)::numeric, 2) as max_duration_ms
FROM tool_executions
GROUP BY tool_name
ORDER BY total_calls DESC;
"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Observability test complete!${NC}"
echo -e "${GREEN}=========================================${NC}"

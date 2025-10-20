#!/bin/bash
#
# Database Helper Script for MCP Server Blueprint
# Usage: ./scripts/db.sh [command]
#

set -e

DB_NAME="mcp_server"
DB_USER="hyalen"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper function to run psql commands
run_psql() {
    psql "$DB_NAME" "$@"
}

# Helper function to run psql with output
run_psql_query() {
    psql "$DB_NAME" -c "$1"
}

# Show usage
show_usage() {
    echo -e "${BLUE}MCP Server Database Helper${NC}"
    echo ""
    echo "Usage: ./scripts/db.sh [command]"
    echo ""
    echo "Commands:"
    echo "  connect         - Open psql interactive shell"
    echo "  tools           - List all tools"
    echo "  tools-active    - List only active tools"
    echo "  params          - Show tools with their parameters"
    echo "  schema          - Show database schema"
    echo "  size            - Show database size"
    echo "  reset           - Reset database (WARNING: deletes all data)"
    echo "  backup          - Backup database to file"
    echo "  restore [file]  - Restore database from backup file"
    echo "  query [sql]     - Run a custom SQL query"
    echo "  logs            - Show recent database activity"
    echo ""
    echo "Examples:"
    echo "  ./scripts/db.sh tools"
    echo "  ./scripts/db.sh query \"SELECT * FROM tools WHERE is_active = true\""
    echo ""
}

# Connect to database
cmd_connect() {
    echo -e "${GREEN}Connecting to $DB_NAME...${NC}"
    run_psql
}

# List all tools
cmd_tools() {
    echo -e "${GREEN}All Tools:${NC}"
    run_psql_query "
        SELECT
            id,
            name,
            description,
            is_active,
            created_at
        FROM tools
        ORDER BY name;
    "
}

# List active tools
cmd_tools_active() {
    echo -e "${GREEN}Active Tools:${NC}"
    run_psql_query "
        SELECT
            name,
            description
        FROM tools
        WHERE is_active = true
        ORDER BY name;
    "
}

# Show tools with parameters
cmd_params() {
    echo -e "${GREEN}Tools with Parameters:${NC}"
    run_psql_query "
        SELECT
            t.name as tool_name,
            t.is_active,
            tp.name as param_name,
            tp.type as param_type,
            tp.required,
            tp.description as param_description
        FROM tools t
        LEFT JOIN tool_parameters tp ON t.id = tp.tool_id
        ORDER BY t.name, tp.name;
    "
}

# Show database schema
cmd_schema() {
    echo -e "${GREEN}Database Schema:${NC}"
    echo ""
    echo -e "${BLUE}Tables:${NC}"
    run_psql_query "\dt"
    echo ""
    echo -e "${BLUE}Tools Table:${NC}"
    run_psql_query "\d tools"
    echo ""
    echo -e "${BLUE}Tool Parameters Table:${NC}"
    run_psql_query "\d tool_parameters"
}

# Show database size
cmd_size() {
    echo -e "${GREEN}Database Size:${NC}"
    run_psql_query "
        SELECT
            pg_size_pretty(pg_database_size('$DB_NAME')) as database_size,
            pg_size_pretty(pg_total_relation_size('tools')) as tools_table_size,
            pg_size_pretty(pg_total_relation_size('tool_parameters')) as params_table_size;
    "
    echo ""
    echo -e "${GREEN}Record Counts:${NC}"
    run_psql_query "
        SELECT
            (SELECT COUNT(*) FROM tools) as tools_count,
            (SELECT COUNT(*) FROM tool_parameters) as parameters_count;
    "
}

# Reset database
cmd_reset() {
    echo -e "${YELLOW}WARNING: This will delete all data and recreate the database!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi

    echo -e "${GREEN}Resetting database...${NC}"
    cd "$(dirname "$0")/.."
    uv run python scripts/init_db.py
    echo -e "${GREEN}Database reset complete!${NC}"
}

# Backup database
cmd_backup() {
    BACKUP_FILE="backups/mcp_server_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p backups
    echo -e "${GREEN}Backing up database to $BACKUP_FILE...${NC}"
    pg_dump "$DB_NAME" > "$BACKUP_FILE"
    echo -e "${GREEN}Backup complete!${NC}"
    echo "File: $BACKUP_FILE"
}

# Restore database
cmd_restore() {
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Error: Please provide backup file path${NC}"
        echo "Usage: ./scripts/db.sh restore <backup_file>"
        exit 1
    fi

    if [ ! -f "$1" ]; then
        echo -e "${YELLOW}Error: Backup file not found: $1${NC}"
        exit 1
    fi

    echo -e "${YELLOW}WARNING: This will overwrite the current database!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi

    echo -e "${GREEN}Restoring database from $1...${NC}"
    psql "$DB_NAME" < "$1"
    echo -e "${GREEN}Restore complete!${NC}"
}

# Run custom query
cmd_query() {
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Error: Please provide SQL query${NC}"
        echo "Usage: ./scripts/db.sh query \"SELECT * FROM tools\""
        exit 1
    fi

    echo -e "${GREEN}Running query:${NC} $1"
    run_psql_query "$1"
}

# Show logs (if you have logging enabled)
cmd_logs() {
    echo -e "${GREEN}Recent Database Activity:${NC}"
    run_psql_query "
        SELECT
            t.name,
            t.is_active,
            t.created_at,
            t.updated_at
        FROM tools t
        ORDER BY t.updated_at DESC
        LIMIT 10;
    "
}

# Main command router
case "${1:-}" in
    "")
        show_usage
        ;;
    connect)
        cmd_connect
        ;;
    tools)
        cmd_tools
        ;;
    tools-active)
        cmd_tools_active
        ;;
    params)
        cmd_params
        ;;
    schema)
        cmd_schema
        ;;
    size)
        cmd_size
        ;;
    reset)
        cmd_reset
        ;;
    backup)
        cmd_backup
        ;;
    restore)
        cmd_restore "$2"
        ;;
    query)
        cmd_query "$2"
        ;;
    logs)
        cmd_logs
        ;;
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac

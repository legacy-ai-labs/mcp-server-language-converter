## Database Guide

This document describes the database architecture, setup, and management for the MCP Server Blueprint.

## Database Architecture

The application uses PostgreSQL as its primary database with async support via SQLAlchemy and asyncpg.

### Schema Overview

#### Tools Table

The `tools` table stores metadata about available MCP tools:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, auto-increment |
| `name` | VARCHAR(100) | Unique tool name, indexed |
| `description` | TEXT | Tool description |
| `handler_name` | VARCHAR(100) | Name of the Python handler function |
| `parameters_schema` | JSON | JSON Schema for tool parameters |
| `category` | VARCHAR(50) | Tool category (utility, calculation, search, etc.), indexed |
| `domain` | VARCHAR(50) | Tool domain (general, os_commands, kubernetes, etc.), indexed |
| `is_active` | BOOLEAN | Whether the tool is active, indexed |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

### Indexes

- `name` - Unique index for fast lookup by name
- `category` - Index for filtering by category
- `domain` - Index for filtering by domain
- `is_active` - Index for filtering active tools

### Tool Classification

**Categories** (functional grouping):
- `utility` - General utility tools (echo, format, etc.)
- `calculation` - Mathematical operations (add, subtract, etc.)
- `search` - Search and discovery tools
- `system` - System-level operations

**Domains** (business domains):
- `general` - General purpose tools
- `os_commands` - Operating system commands
- `kubernetes` - Kubernetes operations
- `shopping` - E-commerce tools

## PostgreSQL Setup

### Installation

#### macOS (Homebrew)
```bash
brew install postgresql@16
brew services start postgresql@16
```

#### Windows (Chocolatey)
```powershell
choco install postgresql
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

### Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database
CREATE DATABASE mcp_server;

# Create user (optional)
CREATE USER mcp_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE mcp_server TO mcp_user;
```

### Configuration

Create a `.env` file in the project root:

```bash
cp env.example .env
```

Edit `.env` with your database credentials:

```
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/mcp_server
```

## Database Initialization

### 1. Create Tables

```bash
uv run python scripts/init_db.py
```

This will create all necessary tables in the database.

### 2. Seed Initial Tools

```bash
uv run python scripts/seed_tools.py
```

This will populate the database with initial tools:
- **echo**: Echo back text
- **calculator_add**: Add two numbers

## Database Operations

### Manual Tool Management

You can manually manage tools using Python scripts or the PostgreSQL CLI.

#### Connect to Database

```bash
psql postgresql://username:password@localhost:5432/mcp_server
```

#### Query Tools

```sql
-- List all tools
SELECT id, name, handler_name, is_active FROM tools;

-- List active tools
SELECT * FROM tools WHERE is_active = true;

-- Get specific tool
SELECT * FROM tools WHERE name = 'echo';
```

#### Insert Tool

```sql
INSERT INTO tools (name, description, handler_name, parameters_schema, is_active)
VALUES (
    'my_tool',
    'My custom tool',
    'echo_handler',
    '{"type": "object", "properties": {"text": {"type": "string"}}}',
    true
);
```

#### Update Tool

```sql
-- Deactivate a tool
UPDATE tools SET is_active = false WHERE name = 'echo';

-- Update description
UPDATE tools SET description = 'New description' WHERE id = 1;
```

#### Delete Tool

```sql
-- Soft delete (recommended)
UPDATE tools SET is_active = false WHERE id = 1;

-- Hard delete (caution)
DELETE FROM tools WHERE id = 1;
```

## Migrations (Future)

The project is set up to use Alembic for database migrations. Migration support will be added in a future update.

To prepare for migrations:

```bash
# Initialize Alembic (future)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

## Backup and Restore

### Backup Database

```bash
pg_dump -U username mcp_server > backup.sql
```

### Restore Database

```bash
psql -U username mcp_server < backup.sql
```

## Troubleshooting

### Connection Issues

**Problem**: Can't connect to PostgreSQL

**Solutions**:
1. Check PostgreSQL is running: `brew services list` (macOS) or `sudo systemctl status postgresql` (Linux)
2. Verify credentials in `.env`
3. Check firewall settings
4. Ensure PostgreSQL is listening on correct port: `netstat -an | grep 5432`

### Permission Issues

**Problem**: Permission denied for database

**Solution**:
```sql
GRANT ALL PRIVILEGES ON DATABASE mcp_server TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
```

### Migration Issues

**Problem**: Tables don't exist

**Solution**:
```bash
# Recreate tables
uv run python scripts/init_db.py
```

## Performance Optimization

### Connection Pooling

The application uses SQLAlchemy's async connection pooling. Default settings work well for most cases, but you can tune in `src/core/database.py`:

```python
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=5,          # Adjust based on load
    max_overflow=10,      # Additional connections when needed
    pool_pre_ping=True,   # Check connections before using
)
```

### Indexing

All critical columns are indexed:
- `tools.name` (unique)
- `tools.is_active`

### Query Optimization

- Use `list_active()` instead of `list_all()` when possible
- Avoid loading unnecessary relationships
- Use pagination for large result sets (to be implemented)

## Database Monitoring

### Check Database Size

```sql
SELECT pg_size_pretty(pg_database_size('mcp_server'));
```

### Check Table Sizes

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monitor Active Connections

```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'mcp_server';
```

## Best Practices

1. **Always use migrations** for schema changes (when implemented)
2. **Use soft deletes** (`is_active = false`) instead of hard deletes
3. **Back up regularly** before major changes
4. **Test on development database** first
5. **Use transactions** for multi-step operations
6. **Monitor connection pool** in production

## Security

1. **Never commit `.env`** file to version control
2. **Use strong passwords** for database users
3. **Restrict network access** to PostgreSQL port
4. **Use SSL** for remote connections
5. **Regular security updates** for PostgreSQL

---

For more information, see:
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

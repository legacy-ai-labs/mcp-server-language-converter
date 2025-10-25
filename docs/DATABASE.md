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

### Database Creation

```bash
# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE mcp_server;
CREATE USER mcp_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE mcp_server TO mcp_user;
```

### Environment Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://mcp_user:your_password@localhost:5432/mcp_server
DATABASE_ECHO=false
```

## Database Initialization

### Initialize Tables

```bash
# Create all tables
uv run python scripts/init_db.py
```

### Seed Initial Data

```bash
# Add sample tools
uv run python scripts/seed_tools.py
```

## Database Operations

### Connection Management

The application uses async database connections with connection pooling:

```python
from src.core.database import get_db

async def some_operation():
    async with get_db() as db:
        # Use database session
        pass
```

### Tool Management

#### Adding Tools

```python
from src.core.repositories.tool_repository import ToolRepository
from src.core.schemas.tool import ToolCreate

async def add_tool():
    async with get_db() as db:
        repo = ToolRepository(db)
        tool_data = ToolCreate(
            name="my_tool",
            description="A custom tool",
            handler_name="my_handler",
            parameters_schema={"type": "object"},
            category="utility",
            domain="general"
        )
        tool = await repo.create(tool_data.model_dump())
```

#### Querying Tools

```python
# Get all active tools
tools = await repo.list_active()

# Get tools by domain
tools = await repo.get_by_domain("general")

# Get tool by name
tool = await repo.get_by_name("echo")
```

## Migrations (Future)

The project will implement Alembic migrations for schema changes:

```bash
# Generate migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head
```

## Backup and Restore

### Backup

```bash
# Create backup
pg_dump -h localhost -U mcp_user -d mcp_server > backup.sql

# Compressed backup
pg_dump -h localhost -U mcp_user -d mcp_server | gzip > backup.sql.gz
```

### Restore

```bash
# Restore from backup
psql -h localhost -U mcp_user -d mcp_server < backup.sql

# Restore from compressed backup
gunzip -c backup.sql.gz | psql -h localhost -U mcp_user -d mcp_server
```

## Troubleshooting

### Common Issues

**Connection Refused:**
- Check if PostgreSQL is running
- Verify connection parameters in `.env`
- Check firewall settings

**Authentication Failed:**
- Verify username and password
- Check user permissions
- Ensure user has access to database

**Table Not Found:**
- Run database initialization: `uv run python scripts/init_db.py`
- Check if models are properly imported

### Debugging

Enable SQL query logging:

```env
DATABASE_ECHO=true
```

Check connection:

```python
from src.core.database import engine
import asyncio

async def test_connection():
    async with engine.begin() as conn:
        result = await conn.execute("SELECT 1")
        print(result.scalar())
```

## Performance Optimization

### Indexing Strategy

- **Primary keys**: Automatically indexed
- **Foreign keys**: Automatically indexed
- **Frequently queried columns**: Add custom indexes
- **Composite indexes**: For multi-column queries

### Connection Pooling

The application uses SQLAlchemy's connection pooling:

```python
# Configure pool settings
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Query Optimization

- Use `select()` with specific columns
- Implement pagination for large result sets
- Use database-level filtering instead of Python filtering
- Consider read replicas for heavy read workloads

## Database Monitoring

### Health Checks

```python
async def health_check():
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
            return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Performance Metrics

Monitor key metrics:
- Connection pool usage
- Query execution time
- Database size growth
- Index usage statistics

## Best Practices

1. **Use transactions** for related operations
2. **Handle exceptions** gracefully
3. **Close connections** properly
4. **Use connection pooling** for production
5. **Monitor performance** regularly
6. **Backup regularly** and test restore procedures

## Security

### Database Security

- Use strong passwords
- Limit database user permissions
- Enable SSL connections in production
- Regular security updates
- Network access controls

### Application Security

- Use parameterized queries (SQLAlchemy handles this)
- Validate input data
- Implement rate limiting
- Log security events
- Regular security audits
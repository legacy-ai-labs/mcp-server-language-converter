# MCP Server Blueprint

A **hybrid MCP (Model Context Protocol) server** implementation that supports multiple domain-specific MCP servers, each exposing business logic through multiple interfaces: MCP protocol (STDIO and HTTP streaming) and REST API.

## Purpose

This project demonstrates how to build a modern server that serves both AI agents (via MCP) and traditional applications (via REST API) while maintaining a single source of truth for business logic.

## Key Features

- **Domain-Specific MCP Servers**: Separate MCP servers for different domains (general, OS commands, Kubernetes, etc.)
- **Dual Interface Support**: MCP protocol and REST API using the same core business logic
- **Multiple Transport Layers**: STDIO, HTTP streaming (MCP), and standard REST
- **MCP Capabilities**: Tools, Resources, and Prompts
- **Incremental Development**: Phased approach across capabilities and transport layers
- **Modern Python Stack**: UV for package management, FastMCP 2.0, FastAPI

## Architecture

The application follows a **Hexagonal/Ports and Adapters** architecture pattern:

- **Interface Layer**: MCP Server (FastMCP) and REST API (FastAPI)
- **Core Business Logic Layer**: Transport-agnostic, reusable functions

```mermaid
graph TB
    subgraph Interface["Interface Layer"]
        STDIO["STDIO Server<br/>(FastMCP 2.0)<br/>━━━━━━━━━━━━━<br/>• STDIO transport<br/>• Claude Desktop<br/>• Cursor IDE"]
        HTTP["HTTP Streaming Server<br/>(FastMCP 2.0)<br/>━━━━━━━━━━━━━<br/>• Server-Sent Events<br/>• Web-based clients<br/>• Real-time streaming"]
        REST["REST API<br/>(FastAPI)<br/>━━━━━━━━━━━━━<br/>• HTTP endpoints<br/>• JSON responses<br/>• Standard REST"]
    end

    subgraph Core["Core Business Logic Layer"]
        BL["<b>Shared Functions:</b><br/>• Transport-agnostic<br/>• Reusable across interfaces<br/>• Single source of truth<br/>• Pure business logic"]
    end

    STDIO --> BL
    HTTP --> BL
    REST --> BL

    style Interface fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
    style Core fill:#0d0d0d,stroke:#fff,stroke-width:2px,color:#fff
    style STDIO fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style HTTP fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style REST fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style BL fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
```

For detailed architectural decisions and design patterns, see [Architecture Documentation](docs/ARCHITECTURE.md).

## Multi-Server Architecture with Shared Infrastructure

The project supports **domain-specific MCP servers** with **zero code duplication**:

```
src/
├── core/                    # Shared business logic
│   ├── models/             # Database models
│   ├── repositories/       # Data access layer
│   ├── services/           # Business logic and tool handlers
│   └── schemas/            # Validation schemas
│
├── mcp_servers/
│   ├── common/             # Shared MCP infrastructure (NO duplication!)
│   │   ├── base_server.py          # FastMCP initialization
│   │   ├── dynamic_loader.py       # Generic tool loading from DB
│   │   ├── stdio_runner.py         # Generic STDIO transport
│   │   └── http_runner.py          # Generic HTTP streaming transport
│   │
│   ├── mcp_general/        # Domain servers (minimal code - just entry points)
│   │   ├── __main__.py             # 7 lines
│   │   └── http_main.py            # 7 lines
│   │
│   ├── mcp_kubernetes/     # Future: Same minimal pattern
│   ├── mcp_os_commands/    # Future: Same minimal pattern
│   └── mcp_shopping/       # Future: Same minimal pattern
│
└── rest_api/               # Shared REST API (planned)
```

**Architecture Benefits:**
- **Zero Code Duplication**: All MCP server code is in `common/` - domain servers are just entry points
- **Easy to Add Domains**: New domain server = 14 lines of code (2 files × 7 lines)
- **Separation of Concerns**: Each server handles one domain
- **Shared Infrastructure**: Same database, repositories, services, AND MCP runtime code
- **Independent Scaling**: Each server can be scaled separately
- **Security**: Domain-specific permissions and isolation

### Database-Driven Tools

Tools are now **dynamically loaded from the database** at server startup:

- **Tool Metadata**: Stored in PostgreSQL with category and domain classification
- **Handler Registry**: Predefined Python functions for business logic
- **Dynamic Registration**: Tools loaded from database and registered with FastMCP
- **CRUD Operations**: Full tool management through database operations

**Tool Classification:**
- **Category**: Functional grouping (utility, calculation, search, etc.)
- **Domain**: Business domain (general, os_commands, kubernetes, etc.)


## Quick Start

### Transport Options

The MCP Server Blueprint supports **multiple transport mechanisms** for different client types:

#### STDIO Server (Claude Desktop, Cursor IDE)
- **Transport**: STDIO (standard input/output)
- **Clients**: Claude Desktop, Cursor IDE, command-line tools
- **Protocol**: MCP over STDIO

#### HTTP Streaming Server (Web-based Clients)
- **Transport**: Server-Sent Events (SSE) over HTTP
- **Clients**: Web applications, browser-based AI clients
- **Protocol**: MCP over HTTP streaming

#### Streamable HTTP Server (Full MCP Protocol)
- **Transport**: Streamable HTTP (bidirectional)
- **Clients**: Web applications requiring full MCP protocol
- **Protocol**: MCP over Streamable HTTP with session management

### Separate Server Processes (Recommended)

**Why separate processes?**
- ✅ **Clean separation**: Each transport has a single responsibility
- ✅ **Independent scaling**: Scale each server based on demand
- ✅ **Reliability**: One server failure doesn't affect the other
- ✅ **Different configurations**: Optimize each for its use case
- ✅ **Easier debugging**: Isolate issues to specific transports

**How to start each server:**

```bash
# Terminal 1: STDIO server (for Claude Desktop, Cursor IDE)
uv run python -m src.mcp_servers.mcp_general

# Terminal 2: HTTP streaming server (for web-based clients)
uv run python -m src.mcp_servers.mcp_general.http_main
# Server available at: http://localhost:8000

# Terminal 3: Streamable HTTP server (for full MCP protocol)
uv run python -m src.mcp_servers.mcp_general.streamable_http_main
# Server available at: http://localhost:8002
```

Both servers share the same core business logic and tools, but provide different transport mechanisms for different client types.

### Testing Your Setup

#### STDIO Testing (Claude Desktop)
1. Configure Claude Desktop with the server
2. Test tools through Claude Desktop interface

#### HTTP Streaming Testing
1. **Quick test with curl:**
   ```bash
   curl -N -H "Accept: text/event-stream" http://localhost:8000/sse
   ```

2. **MCP Inspector (Recommended):**
   ```bash
   npx @modelcontextprotocol/inspector
   # Open http://localhost:3000 and connect to http://localhost:8000/sse
   ```

3. **Comprehensive testing guide:** See [HTTP Streaming Guide](docs/HTTP_STREAMING.md#testing-http-streaming)

#### Streamable HTTP Testing
1. **Python client test:**
   ```bash
   uv run python test_streamable_http_client.py
   ```

2. **Test both transports:**
   ```bash
   uv run python test_both_transports.py
   ```

3. **Comprehensive guide:** See [Streamable HTTP Guide](docs/STREAMABLE_HTTP.md)

### Prerequisites

- **Python 3.12+**
- **UV** (Python package manager)
- **PostgreSQL 14+** (database)
- **Docker** (optional, for containerized deployment)
- **Cursor IDE** with Claude Code integration (recommended)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mcp-server-blueprint

# Install UV (if not already installed)
# macOS (Homebrew)
brew install uv

# Windows (Chocolatey)
choco install uv

# Install dependencies
uv sync

# Set up pre-commit hooks
uv run pre-commit install
```

### Database Setup

```bash
# Install PostgreSQL
# macOS
brew install postgresql@16
brew services start postgresql@16

# Windows
choco install postgresql

# Create database
createdb mcp_server

# Configure environment
cp env.example .env
# Edit .env with your database credentials

# Initialize database and seed data
uv run python scripts/init_db.py
uv run python scripts/seed_tools.py
```

### Running the Server

```bash
# Initialize database and seed tools
uv run python scripts/init_db.py
uv run python scripts/seed_tools.py

# Run General MCP server (STDIO mode)
uv run python -m src.mcp_servers.mcp_general

# Future: Run other domain-specific servers
# uv run python -m src.mcp_servers.mcp_os_commands
# uv run python -m src.mcp_servers.mcp_kubernetes
# uv run python -m src.mcp_servers.mcp_shopping

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | Architectural decisions, design patterns, and development phases |
| [Setup Guide](docs/SETUP.md) | Development environment setup, tools, and configuration |
| [Database Guide](docs/DATABASE.md) | Database schema, setup, migrations, and management |
| [Usage Guide](docs/USAGE.md) | Common usage patterns and examples |
| [Contributing](docs/CONTRIBUTING.md) | Guidelines for contributing to the project |
| [API Documentation](docs/API.md) | MCP tools/resources/prompts and REST endpoint reference |

## Technology Stack

- **Language**: Python 3.12+
- **Package Manager**: [UV](https://github.com/astral-sh/uv) - Fast Python package installer
- **MCP Framework**: [FastMCP 2.0](https://github.com/jlowin/fastmcp) - STDIO and HTTP streaming support
- **REST Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance REST API
- **Database**: [PostgreSQL](https://www.postgresql.org/) with async support (SQLAlchemy + asyncpg)
- **Development Tools**:
  - Cursor IDE with Claude Code integration
  - Pre-commit hooks for code quality
  - Docker for containerization
  - Ruff for linting and formatting
  - Pytest for testing

## Development Phases

The project is developed in **three major phases**, each with **three sub-steps**:

```mermaid
graph LR
    subgraph Phase1["Phase 1: Tools"]
        T1["1.1<br/>STDIO"]
        T2["1.2<br/>HTTP Streaming"]
        T3["1.3<br/>REST API"]
        T1 --> T2 --> T3
    end

    subgraph Phase2["Phase 2: Resources"]
        R1["2.1<br/>STDIO"]
        R2["2.2<br/>HTTP Streaming"]
        R3["2.3<br/>REST API"]
        R1 --> R2 --> R3
    end

    subgraph Phase3["Phase 3: Prompts"]
        P1["3.1<br/>STDIO"]
        P2["3.2<br/>HTTP Streaming"]
        P3["3.3<br/>REST API"]
        P1 --> P2 --> P3
    end

    Phase1 --> Phase2 --> Phase3

    style Phase1 fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
    style Phase2 fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
    style Phase3 fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
    style T1 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style T2 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style T3 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style R1 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style R2 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style R3 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style P1 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style P2 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style P3 fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
```

**Summary:**
- **Phase 1: Tools** - Implement MCP tools across all transport layers
- **Phase 2: Resources** - Add MCP resources across all transport layers  
- **Phase 3: Prompts** - Implement MCP prompts across all transport layers

Each phase follows the same pattern: STDIO → HTTP Streaming → REST API

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed phase breakdown.

## Contributing

We welcome contributions! Please read our [Contributing Guidelines](docs/CONTRIBUTING.md) before submitting PRs.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

## License

[Add your license here]

## Documentation

- [HTTP Streaming Guide](docs/HTTP_STREAMING.md) - Complete guide for SSE transport implementation
- [Streamable HTTP Guide](docs/STREAMABLE_HTTP.md) - Complete guide for Streamable HTTP transport
- [Usage Guide](docs/USAGE.md) - Detailed usage instructions for all transport modes
- [Architecture Documentation](docs/ARCHITECTURE.md) - System design and architectural decisions
- [Database Guide](docs/DATABASE.md) - Database setup and management
- [API Documentation](docs/API.md) - REST API reference
- [Contributing Guidelines](docs/CONTRIBUTING.md) - Development workflow and standards

## Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [UV Documentation](https://github.com/astral-sh/uv)

## Contact

[Add your contact information here]

---

**Built with Cursor + Claude Code**

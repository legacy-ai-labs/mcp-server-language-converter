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
        MCP["MCP Server<br/>(FastMCP 2.0)<br/>━━━━━━━━━━━━━<br/>• STDIO transport<br/>• HTTP streaming<br/>• MCP protocol"]
        REST["REST API<br/>(FastAPI)<br/>━━━━━━━━━━━━━<br/>• HTTP endpoints<br/>• JSON responses<br/>• Standard REST"]
    end

    subgraph Core["Core Business Logic Layer"]
        BL["<b>Functions:</b><br/>• Transport-agnostic<br/>• Reusable across interfaces<br/>• Single source of truth<br/>• Pure business logic"]
    end

    MCP --> BL
    REST --> BL

    style Interface fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
    style Core fill:#0d0d0d,stroke:#fff,stroke-width:2px,color:#fff
    style MCP fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style REST fill:#2d2d2d,stroke:#fff,stroke-width:2px,color:#fff
    style BL fill:#1a1a1a,stroke:#fff,stroke-width:2px,color:#fff
```

For detailed architectural decisions and design patterns, see [Architecture Documentation](docs/ARCHITECTURE.md).

## Multi-Server Architecture

The project supports **domain-specific MCP servers** for better organization and scalability:

```
src/
├── core/                    # Shared business logic
│   ├── models/             # Database models
│   ├── repositories/       # Data access layer
│   ├── services/           # Business logic
│   └── schemas/            # Validation schemas
├── mcp_servers/            # Domain-specific MCP servers
│   ├── general/            # General purpose tools (echo, calculator)
│   ├── os_commands/        # OS-specific tools (future)
│   ├── kubernetes/         # K8s-specific tools (future)
│   └── shopping/           # E-commerce tools (future)
└── rest_api/               # Shared REST API
```

**Benefits:**
- **Separation of Concerns**: Each server handles one domain
- **Shared Infrastructure**: Same database, repositories, and services
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
uv run python -m src.mcp_servers.general

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

## Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [UV Documentation](https://github.com/astral-sh/uv)

## Contact

[Add your contact information here]

---

**Built with Cursor + Claude Code**

# Development Setup Guide

This guide covers everything you need to set up your development environment for the MCP Server Language Converter project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [IDE Setup (Cursor)](#ide-setup-cursor)
- [Python Environment](#python-environment)
- [Package Management (UV)](#package-management-uv)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Docker Setup](#docker-setup)
- [FastMCP Configuration](#fastmcp-configuration)
- [FastAPI Configuration](#fastapi-configuration)
- [Verification](#verification)

---

## Prerequisites

### Operating System Requirements

#### macOS
- macOS 11.0 or later
- [Homebrew](https://brew.sh/) package manager

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Windows
- Windows 10/11
- [Chocolatey](https://chocolatey.org/) package manager

```powershell
# Install Chocolatey (run PowerShell as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

---

## IDE Setup (Cursor)

[Cursor](https://cursor.sh/) is an AI-first IDE built on VSCode that integrates Claude Code for AI-assisted development.

### Installation

#### macOS
```bash
# Download from website
open https://cursor.sh/

# Or via Homebrew Cask
brew install --cask cursor
```

#### Windows
```powershell
# Download from website or use Chocolatey
choco install cursor
```

### Claude Code Integration

1. **Open Cursor Settings**
   - Press `Cmd+,` (macOS) or `Ctrl+,` (Windows)
   - Or click on the gear icon in the bottom left

2. **Navigate to Cursor Settings**
   - Click on "Cursor" tab in settings
   - Select "Models" section

3. **Configure Claude Model**
   - Under "Chat Model", select **Claude Sonnet 4.5** (or latest version)
   - Enter your Anthropic API key if required
   - Enable "Claude Code" features

4. **API Key Setup**
   - Go to [Anthropic Console](https://console.anthropic.com/)
   - Generate an API key
   - In Cursor: Settings → Cursor → Models → Add API Key

### Cursor Rules Configuration

Cursor Rules help Claude Code understand your project's context and coding standards. Create a `.cursorrules` file in the project root:

```bash
# Create .cursorrules file
touch .cursorrules
```

**Recommended `.cursorrules` content:**

```
# MCP Server Language Converter - Cursor Rules

## Project Context
This is a hybrid MCP (Model Context Protocol) server that exposes business logic through:
- MCP protocol (STDIO and HTTP streaming) using FastMCP 2.0
- REST API using FastAPI

## Architecture Principles
- Hexagonal/Ports and Adapters architecture
- Core business logic is transport-agnostic
- All business logic must be reusable across MCP and REST interfaces
- Never duplicate business logic between interfaces

## Code Style
- Python 3.12+ features encouraged
- Type hints required for all function signatures
- Use Ruff for linting and formatting
- Follow PEP 8 conventions
- Use async/await for I/O operations

## File Organization
- `src/core/` - Transport-agnostic business logic
- `src/mcp_server/` - MCP interface layer (FastMCP)
- `src/rest_api/` - REST interface layer (FastAPI)
- `tests/` - Test files mirroring src/ structure

## Testing Requirements
- Unit tests for all business logic functions
- Integration tests for both MCP and REST interfaces
- Use pytest for all tests
- Aim for >80% code coverage

## Documentation
- Docstrings required for all public functions/classes
- Use Google-style docstrings
- Update relevant docs/ files when architecture changes

## MCP Development
- Tools, Resources, and Prompts must follow MCP specification
- Always define proper schemas for MCP tools
- Handle MCP errors gracefully with appropriate error codes

## REST API Development
- Use FastAPI's automatic OpenAPI documentation
- Follow RESTful conventions (GET, POST, PUT, DELETE)
- Return appropriate HTTP status codes
- Use Pydantic models for request/response validation

## Pre-commit Hooks
- All commits must pass pre-commit checks
- Run `uv run pre-commit run --all-files` before pushing

## Development Workflow
- Create feature branches from main
- Write tests before implementing features (TDD encouraged)
- Ensure all tests pass before committing
- Keep commits atomic and well-described
```

### Cursor Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Open AI chat panel |
| `Cmd/Ctrl + L` | Ask Claude Code to edit current file |
| `Cmd/Ctrl + Shift + L` | Ask Claude Code about selection |
| `Cmd/Ctrl + I` | Inline AI editing |
| `Cmd/Ctrl + .` | Quick fix / Code actions |

### Cursor Workspace Settings

Create `.vscode/settings.json` for project-specific settings:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".venv": false
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "ruff.lint.run": "onSave"
}
```

---

## Python Environment

### Install Python 3.12+

#### macOS
```bash
# Using Homebrew
brew install python@3.12

# Verify installation
python3.12 --version
```

#### Windows
```powershell
# Using Chocolatey
choco install python --version=3.12.0

# Verify installation
python --version
```

#### Alternative: Using pyenv

```bash
# Install pyenv
# macOS
brew install pyenv

# Windows
choco install pyenv-win

# Install Python 3.12
pyenv install 3.12.0
pyenv global 3.12.0
```

---

## Package Management (UV)

[UV](https://github.com/astral-sh/uv) is an extremely fast Python package installer and resolver, written in Rust.

### Why UV?

- **10-100x faster** than pip
- Built-in virtual environment management
- Compatible with pip and pyproject.toml
- Reliable dependency resolution
- Cross-platform support

### Installation

#### macOS
```bash
# Using Homebrew
brew install uv

# Or using curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows
```powershell
# Using Chocolatey
choco install uv

# Or using PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Verify Installation

```bash
uv --version
```

### Initialize Project

```bash
# Navigate to project directory
cd mcp-server-language-converter

# Initialize UV project (if not already done)
uv init

# Create virtual environment and install dependencies
uv sync

# The .venv directory will be created automatically
```

### UV Commands Reference

```bash
# Install a package
uv pip install package-name

# Install from requirements.txt
uv pip install -r requirements.txt

# Add a package to pyproject.toml
uv add package-name

# Remove a package
uv remove package-name

# Update all dependencies
uv sync --upgrade

# Run a command in the virtual environment
uv run python script.py

# Activate virtual environment manually
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Project Dependencies

The project uses the following key dependencies:

```toml
# pyproject.toml (example)
[project]
name = "mcp-server-language-converter"
version = "0.1.0"
description = "Hybrid MCP Server with REST API"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=2.0.0",
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.2.0",
    "pre-commit>=3.6.0",
    "mypy>=1.8.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.2.0",
    "pre-commit>=3.6.0",
    "mypy>=1.8.0",
]
```

---

## Pre-commit Hooks

Pre-commit hooks ensure code quality by running automated checks before each commit.

### Installation

```bash
# Install pre-commit package (should be in dev dependencies)
uv add --dev pre-commit

# Install the git hooks
uv run pre-commit install
```

### Configuration

Create `.pre-commit-config.yaml` in the project root:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.1
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict, --ignore-missing-imports]
```

### Usage

```bash
# Run pre-commit on all files
uv run pre-commit run --all-files

# Run pre-commit on staged files only
git add .
uv run pre-commit run

# Skip pre-commit hooks (not recommended)
git commit --no-verify -m "message"

# Update pre-commit hooks to latest versions
uv run pre-commit autoupdate
```

### Ruff Configuration

Create `ruff.toml` or add to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501", # line too long (handled by formatter)
    "B008", # do not perform function calls in argument defaults
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

---

## Docker Setup

### Install Docker

#### macOS
```bash
# Using Homebrew
brew install --cask docker

# Or download Docker Desktop
open https://www.docker.com/products/docker-desktop
```

#### Windows
```powershell
# Using Chocolatey
choco install docker-desktop

# Or download Docker Desktop
start https://www.docker.com/products/docker-desktop
```

### Verify Installation

```bash
docker --version
docker compose version
```

### Project Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/

# Expose ports
EXPOSE 8000 8001

# Run the application
CMD ["uv", "run", "python", "-m", "src.main"]
```

### Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    container_name: mcp-server
    ports:
      - "8000:8000"  # MCP HTTP
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=info
    volumes:
      - ./src:/app/src
    restart: unless-stopped

  rest-api:
    build: .
    container_name: rest-api
    ports:
      - "8001:8001"  # REST API
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=info
    volumes:
      - ./src:/app/src
    restart: unless-stopped
```

### Docker Commands

```bash
# Build images
docker compose build

# Start services
docker compose up

# Start in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Remove volumes
docker compose down -v

# Rebuild and start
docker compose up --build
```

---

## FastMCP Configuration

[FastMCP 2.0](https://github.com/jlowin/fastmcp) provides both STDIO and HTTP streaming support for MCP servers.

### Installation

```bash
uv add fastmcp
```

### Basic Configuration

```python
# src/mcp_server/server.py
from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("mcp-server-language-converter")

# Configure server settings
mcp.settings(
    name="MCP Server Language Converter",
    version="0.1.0",
    description="Hybrid MCP server with REST API support"
)
```

### STDIO Transport

```python
# Run MCP server with STDIO
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### HTTP Streaming Transport

```python
# Run MCP server with HTTP streaming
if __name__ == "__main__":
    mcp.run(
        transport="sse",  # Server-Sent Events
        host="0.0.0.0",
        port=8000
    )
```

### Running FastMCP Server

```bash
# STDIO mode (for Cursor/Claude Desktop)
uv run python -m src.mcp_server

# HTTP streaming mode
uv run python -m src.mcp_server --transport=sse --port=8000
```

---

## FastAPI Configuration

[FastAPI](https://fastapi.tiangolo.com/) provides the REST API interface.

### Installation

```bash
uv add fastapi uvicorn[standard]
```

### Basic Configuration

```python
# src/rest_api/server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI
app = FastAPI(
    title="MCP Server Language Converter REST API",
    version="0.1.0",
    description="REST API interface for MCP Server Language Converter",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Running FastAPI Server

```bash
# Development mode with auto-reload
uv run uvicorn src.rest_api.server:app --reload --port 8001

# Production mode
uv run uvicorn src.rest_api.server:app --host 0.0.0.0 --port 8001 --workers 4
```

### Access Documentation

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

---

## Verification

### Verify Complete Setup

Run this checklist to ensure everything is set up correctly:

```bash
# 1. Check Python version
python3 --version  # Should be 3.12+

# 2. Check UV installation
uv --version

# 3. Check virtual environment
uv run python -c "import sys; print(sys.prefix)"

# 4. Install all dependencies
uv sync

# 5. Run pre-commit checks
uv run pre-commit run --all-files

# 6. Check Docker
docker --version
docker compose version

# 7. Run tests (when available)
uv run pytest

# 8. Check linting
uv run ruff check .

# 9. Check formatting
uv run ruff format --check .

# 10. Check type hints
uv run mypy src/
```

### Common Issues

#### Issue: UV not found after installation

**Solution:**
```bash
# Add UV to PATH
export PATH="$HOME/.cargo/bin:$PATH"  # macOS/Linux
# Or restart your terminal
```

#### Issue: Python version mismatch

**Solution:**
```bash
# Use pyenv to manage Python versions
pyenv install 3.12.0
pyenv local 3.12.0
```

#### Issue: Pre-commit hooks failing

**Solution:**
```bash
# Update pre-commit hooks
uv run pre-commit autoupdate

# Clean and reinstall
uv run pre-commit clean
uv run pre-commit install
```

#### Issue: Docker permission denied (Linux)

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

## Next Steps

1. ✅ Verify all installations
2. 📖 Read the [Architecture Documentation](ARCHITECTURE.md)
3. 🔧 Start implementing Phase 1: Tools (STDIO)
4. 🧪 Write tests for your business logic
5. 📝 Contribute to the project

For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

**Need Help?**

- Check the [official documentation links](#technology-stack-documentation)
- Open an issue in the repository
- Consult the project maintainers

### Technology Stack Documentation

- [Python Documentation](https://docs.python.org/3/)
- [UV Documentation](https://github.com/astral-sh/uv)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Cursor Documentation](https://cursor.sh/docs)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Docker Documentation](https://docs.docker.com/)
- [MCP Specification](https://modelcontextprotocol.io/)

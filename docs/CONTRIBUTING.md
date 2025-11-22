# Contributing to MCP Server Blueprint

Thank you for your interest in contributing to the MCP Server Blueprint project! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the project and community
- Show empathy towards other community members

---

## Getting Started

### Prerequisites

Before contributing, ensure you have completed the setup process outlined in [SETUP.md](SETUP.md):

1. ✅ Cursor IDE with Claude Code configured
2. ✅ Python 3.12+ installed
3. ✅ UV package manager installed
4. ✅ Pre-commit hooks configured
5. ✅ Docker installed (optional)

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/mcp-server-language-converter.git
cd mcp-server-language-converter

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/mcp-server-language-converter.git

# Verify remotes
git remote -v
```

### Set Up Development Environment

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Verify setup
uv run pytest
uv run pre-commit run --all-files
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### Branch Naming Conventions

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or updates
- `chore/` - Maintenance tasks

Examples:
- `feature/add-order-tool`
- `fix/mcp-streaming-error`
- `docs/update-api-reference`

### 2. Make Your Changes

Follow the [Coding Standards](#coding-standards) and [Testing Guidelines](#testing-guidelines).

```bash
# Make your changes
# Run tests frequently
uv run pytest

# Check code quality
uv run ruff check .
uv run ruff format .
```

### 3. Commit Your Changes

Follow the [Commit Guidelines](#commit-guidelines).

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add create_order tool for MCP"

# Pre-commit hooks will run automatically
```

### 4. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Go to GitHub and create a Pull Request
```

---

## Coding Standards

### Architecture Principles

**CRITICAL**: Always follow the hybrid architecture pattern:

1. **Business logic goes in `src/core/`**
   - Must be transport-agnostic
   - No MCP or REST-specific code
   - Reusable across all interfaces

2. **MCP interface goes in `src/mcp_server/`**
   - Handles MCP protocol specifics
   - Calls core business logic
   - Manages MCP schemas and responses

3. **REST interface goes in `src/rest_api/`**
   - Handles HTTP/REST specifics
   - Calls the same core business logic
   - Manages FastAPI routes and models

### Python Style Guide

#### Type Hints

Type hints are **required** for all function signatures:

```python
# ✅ Good
def create_order(order_data: dict[str, Any]) -> Order:
    """Create a new order."""
    ...

# ❌ Bad
def create_order(order_data):
    """Create a new order."""
    ...
```

#### Async/Await

Use async/await for I/O operations:

```python
# ✅ Good
async def fetch_user_data(user_id: int) -> UserData:
    """Fetch user data asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/users/{user_id}")
        return UserData(**response.json())

# ❌ Bad (blocking I/O)
def fetch_user_data(user_id: int) -> UserData:
    """Fetch user data."""
    response = requests.get(f"/users/{user_id}")
    return UserData(**response.json())
```

#### Docstrings

Use Google-style docstrings:

```python
def calculate_total(items: list[OrderItem], tax_rate: float = 0.0) -> float:
    """Calculate the total price for a list of items including tax.

    Args:
        items: List of order items to calculate total for.
        tax_rate: Tax rate to apply (0.0 to 1.0). Defaults to 0.0.

    Returns:
        The total price including tax.

    Raises:
        ValueError: If tax_rate is negative or greater than 1.0.

    Example:
        >>> items = [OrderItem(price=10.0, quantity=2)]
        >>> calculate_total(items, tax_rate=0.1)
        22.0
    """
    if tax_rate < 0 or tax_rate > 1.0:
        raise ValueError("Tax rate must be between 0.0 and 1.0")

    subtotal = sum(item.price * item.quantity for item in items)
    return subtotal * (1 + tax_rate)
```

#### Code Formatting

We use **Ruff** for linting and formatting:

```bash
# Format code
uv run ruff format .

# Check for issues
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .
```

#### Import Organization

Imports should be organized in this order:

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# ✅ Good
import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.core.orders import create_order, validate_order
from src.core.models import Order, OrderItem

# ❌ Bad (mixed order)
from src.core.orders import create_order
import asyncio
from fastapi import FastAPI
from typing import Any
```

### Error Handling

#### Define Custom Exceptions

```python
# src/core/exceptions.py
class BusinessLogicError(Exception):
    """Base exception for business logic errors."""
    pass

class OrderValidationError(BusinessLogicError):
    """Raised when order validation fails."""
    pass

class InsufficientInventoryError(BusinessLogicError):
    """Raised when inventory is insufficient."""
    pass
```

#### Handle Errors at Interface Layer

```python
# MCP Server (src/mcp_server/tools.py)
from mcp import MCPError
from src.core.exceptions import OrderValidationError

@mcp.tool()
async def create_order(order_data: dict) -> dict:
    """MCP tool to create an order."""
    try:
        order = await create_order_logic(order_data)
        return {"success": True, "order_id": order.id}
    except OrderValidationError as e:
        raise MCPError(code="VALIDATION_ERROR", message=str(e))

# REST API (src/rest_api/routes.py)
from fastapi import HTTPException
from src.core.exceptions import OrderValidationError

@app.post("/orders")
async def create_order_endpoint(order_data: OrderCreate) -> OrderResponse:
    """REST endpoint to create an order."""
    try:
        order = await create_order_logic(order_data.dict())
        return OrderResponse(**order.dict())
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## Testing Guidelines

### Testing Philosophy

- **Test business logic thoroughly** (high priority)
- **Test interface layers adequately** (medium priority)
- **Aim for >80% code coverage**
- **Write tests before or alongside implementation** (TDD encouraged)

### Test Structure

```
tests/
├── core/                  # Business logic tests
│   ├── test_orders.py
│   ├── test_payments.py
│   └── test_inventory.py
├── mcp_server/           # MCP interface tests
│   ├── test_tools.py
│   ├── test_resources.py
│   └── test_prompts.py
├── rest_api/             # REST API tests
│   ├── test_endpoints.py
│   └── test_models.py
└── conftest.py           # Shared fixtures
```

### Writing Tests

#### Unit Tests (Business Logic)

```python
# tests/core/test_orders.py
import pytest
from src.core.orders import create_order, validate_order
from src.core.exceptions import OrderValidationError

def test_create_order_success():
    """Test successful order creation."""
    order_data = {
        "customer_id": 123,
        "items": [{"product_id": 1, "quantity": 2}]
    }
    order = create_order(order_data)
    assert order.customer_id == 123
    assert len(order.items) == 1

def test_create_order_invalid_data():
    """Test order creation with invalid data."""
    order_data = {"customer_id": 123}  # Missing items
    with pytest.raises(OrderValidationError):
        create_order(order_data)

@pytest.mark.asyncio
async def test_create_order_async():
    """Test async order creation."""
    order_data = {"customer_id": 123, "items": []}
    order = await create_order_async(order_data)
    assert order is not None
```

#### Integration Tests (MCP Server)

```python
# tests/mcp_server/test_tools.py
import pytest
from fastmcp.testing import MCPTestClient

@pytest.fixture
def mcp_client():
    """Create MCP test client."""
    from src.mcp_server.server import mcp
    return MCPTestClient(mcp)

def test_create_order_tool(mcp_client):
    """Test create_order MCP tool."""
    result = mcp_client.call_tool(
        "create_order",
        arguments={"customer_id": 123, "items": []}
    )
    assert result["success"] is True
    assert "order_id" in result
```

#### Integration Tests (REST API)

```python
# tests/rest_api/test_endpoints.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    """Create FastAPI test client."""
    from src.rest_api.server import app
    return TestClient(app)

def test_create_order_endpoint(client):
    """Test POST /orders endpoint."""
    response = client.post(
        "/orders",
        json={"customer_id": 123, "items": []}
    )
    assert response.status_code == 201
    assert "order_id" in response.json()

def test_create_order_invalid_data(client):
    """Test POST /orders with invalid data."""
    response = client.post("/orders", json={})
    assert response.status_code == 422  # Validation error
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/core/test_orders.py

# Run specific test function
uv run pytest tests/core/test_orders.py::test_create_order_success

# Run tests matching a pattern
uv run pytest -k "order"

# Run with verbose output
uv run pytest -v

# Run and stop on first failure
uv run pytest -x
```

---

## Commit Guidelines

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
# Feature
git commit -m "feat(mcp): add create_order tool with validation"

# Bug fix
git commit -m "fix(rest): correct HTTP status code for validation errors"

# Documentation
git commit -m "docs(setup): add Cursor configuration instructions"

# With body
git commit -m "feat(core): implement order validation logic

Add comprehensive validation for order data including:
- Customer ID validation
- Item quantity checks
- Price validation

Closes #123"
```

### Best Practices

- Keep commits atomic (one logical change per commit)
- Write clear, descriptive commit messages
- Reference issue numbers when applicable
- Use present tense ("add feature" not "added feature")
- Keep subject line under 72 characters

---

## Pull Request Process

### Before Submitting

1. ✅ All tests pass: `uv run pytest`
2. ✅ Code is formatted: `uv run ruff format .`
3. ✅ No linting errors: `uv run ruff check .`
4. ✅ Pre-commit hooks pass: `uv run pre-commit run --all-files`
5. ✅ Documentation updated (if needed)
6. ✅ Commit messages follow guidelines

### PR Title Format

Use the same format as commit messages:

```
feat(mcp): add create_order tool
fix(rest): correct validation error handling
docs(contributing): add testing guidelines
```

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Closes #(issue number)

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe the tests you ran and their results:
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
Add screenshots to help explain your changes.

## Additional Notes
Any additional information that reviewers should know.
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: At least one maintainer reviews the code
3. **Discussion**: Address any feedback or questions
4. **Approval**: Maintainer approves the PR
5. **Merge**: PR is merged into main branch

### After Your PR is Merged

```bash
# Update your local repository
git checkout main
git pull upstream main

# Delete your feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

---

## Project Structure

Understanding the project structure is crucial for contributions:

```
mcp-server-language-converter/
├── .github/                         # GitHub configuration
│   └── workflows/                   # CI/CD workflows
│       └── ci.yml                   # Continuous integration
│
├── docs/                            # Documentation
│   ├── ARCHITECTURE.md              # Architecture decisions & design patterns
│   ├── SETUP.md                     # Development environment setup
│   ├── CONTRIBUTING.md              # This file - contribution guidelines
│   └── API.md                       # API reference (MCP & REST)
│
├── src/                             # Source code
│   ├── __init__.py                  # Package initialization
│   │
│   ├── core/                        # Business logic (transport-agnostic)
│   │   ├── __init__.py              # Core package initialization
│   │   ├── exceptions.py            # Custom exception definitions
│   │   ├── models.py                # Shared data models (Pydantic)
│   │   └── utils.py                 # Shared utility functions
│   │
│   ├── mcp_server/                  # MCP interface layer
│   │   ├── __init__.py              # MCP package initialization
│   │   ├── __main__.py              # Entry point for STDIO mode
│   │   ├── server.py                # MCP server setup & configuration
│   │   ├── tools.py                 # MCP tools implementation
│   │   ├── resources.py             # MCP resources implementation
│   │   └── prompts.py               # MCP prompts implementation
│   │
│   └── rest_api/                    # REST interface layer
│       ├── __init__.py              # REST API package initialization
│       ├── __main__.py              # Entry point for REST server
│       ├── server.py                # FastAPI app setup & configuration
│       ├── routes/                  # REST route handlers
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoints
│       ├── models.py                # Pydantic request/response models
│       ├── dependencies.py          # FastAPI dependencies
│       └── middleware.py            # Custom middleware
│
├── tests/                           # Test files (mirrors src/ structure)
│   ├── __init__.py
│   ├── conftest.py                  # Pytest configuration & shared fixtures
│   │
│   ├── core/                        # Tests for core business logic
│   │   ├── __init__.py
│   │   ├── test_exceptions.py
│   │   ├── test_models.py
│   │   └── test_utils.py
│   │
│   ├── mcp_server/                  # Tests for MCP interface
│   │   ├── __init__.py
│   │   ├── test_server.py
│   │   ├── test_tools.py
│   │   ├── test_resources.py
│   │   └── test_prompts.py
│   │
│   └── rest_api/                    # Tests for REST interface
│       ├── __init__.py
│       ├── test_server.py
│       ├── test_routes.py
│       └── test_models.py
│
├── .vscode/                         # VS Code / Cursor workspace settings
│   └── settings.json                # Editor configuration
│
├── .cursorignore                    # Files to ignore in Cursor
├── .cursorrules                     # Cursor IDE rules for AI assistance
├── .gitignore                       # Git ignore patterns
├── .pre-commit-config.yaml          # Pre-commit hooks configuration
├── .python-version                  # Python version for pyenv
│
├── pyproject.toml                   # Project metadata & dependencies (PEP 621)
├── uv.lock                          # UV lock file (auto-generated)
├── ruff.toml                        # Ruff linter & formatter configuration
│
├── Dockerfile                       # Docker image configuration
├── docker-compose.yml               # Docker Compose multi-container setup
├── .dockerignore                    # Files to ignore in Docker builds
│
├── LICENSE                          # Project license
└── README.md                        # Project overview & quick start
```

### Key Principles

1. **Core business logic** (`src/core/`) must be reusable
2. **Interface layers** (`src/mcp_server/`, `src/rest_api/`) adapt core logic to specific protocols
3. **Never duplicate business logic** between interfaces
4. **Tests mirror source structure** in `tests/` directory

---

## Questions or Problems?

- 📖 Check the [documentation](../README.md)
- 💬 Open a [GitHub Discussion](https://github.com/your-repo/discussions)
- 🐛 Report bugs via [GitHub Issues](https://github.com/your-repo/issues)
- 📧 Contact maintainers (add contact info)

---

Thank you for contributing to MCP Server Blueprint! 🎉

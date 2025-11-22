# API Reference

This document provides a comprehensive reference for both the MCP (Model Context Protocol) interface and REST API interface of the MCP Server Blueprint.

## Table of Contents

- [MCP Interface](#mcp-interface)
  - [Tools](#mcp-tools)
  - [Resources](#mcp-resources)
  - [Prompts](#mcp-prompts)
- [REST API Interface](#rest-api-interface)
  - [Endpoints](#rest-endpoints)
  - [Models](#rest-models)
- [Shared Business Logic](#shared-business-logic)

---

## MCP Interface

The MCP interface provides AI agents with tools, resources, and prompts through both STDIO and HTTP streaming transports.

### Connection Methods

#### STDIO Transport

Used primarily by desktop AI applications like Claude Desktop and Cursor.

```json
{
  "mcpServers": {
    "mcp-server-language-converter": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.mcp_server"],
      "env": {}
    }
  }
}
```

#### HTTP Streaming Transport (SSE)

Used for web-based AI applications and services.

```
Endpoint: http://localhost:8000/sse
Method: Server-Sent Events (SSE)
```

---

## MCP Tools

Tools allow AI agents to execute functions and operations.

### Tool: `example_tool`

**Description**: This is a placeholder for the first tool to be implemented in Phase 1.

**Status**: 🚧 To be implemented

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "param1": {
      "type": "string",
      "description": "First parameter"
    },
    "param2": {
      "type": "number",
      "description": "Second parameter"
    }
  },
  "required": ["param1"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "Whether the operation was successful"
    },
    "result": {
      "type": "string",
      "description": "Result of the operation"
    }
  }
}
```

**Example Usage** (via MCP):
```python
# AI agent calls the tool
result = await mcp_client.call_tool(
    "example_tool",
    arguments={"param1": "test", "param2": 42}
)
# Returns: {"success": true, "result": "..."}
```

**Error Codes**:
- `INVALID_INPUT`: Input validation failed
- `INTERNAL_ERROR`: Internal processing error

---

## MCP Resources

Resources provide AI agents with access to data and content.

### Resource: `example_resource`

**Description**: This is a placeholder for the first resource to be implemented in Phase 2.

**Status**: 🚧 To be implemented

**URI Pattern**: `resource://example/{id}`

**Parameters**:
- `id` (required): Resource identifier

**Response Format**:
```json
{
  "uri": "resource://example/123",
  "mimeType": "application/json",
  "content": {
    "id": "123",
    "data": "..."
  }
}
```

**Example Usage** (via MCP):
```python
# AI agent reads the resource
resource = await mcp_client.read_resource("resource://example/123")
# Returns resource content
```

---

## MCP Prompts

Prompts provide reusable prompt templates for AI agents.

### Prompt: `example_prompt`

**Description**: This is a placeholder for the first prompt to be implemented in Phase 3.

**Status**: 🚧 To be implemented

**Arguments**:
```json
{
  "type": "object",
  "properties": {
    "context": {
      "type": "string",
      "description": "Context for the prompt"
    }
  }
}
```

**Template**:
```
You are an AI assistant helping with {context}.

Please provide a detailed response that includes:
1. Analysis of the situation
2. Recommended actions
3. Potential risks
```

**Example Usage** (via MCP):
```python
# AI agent gets the prompt
prompt = await mcp_client.get_prompt(
    "example_prompt",
    arguments={"context": "order processing"}
)
# Returns formatted prompt
```

---

## REST API Interface

The REST API provides traditional HTTP endpoints for web applications and services.

### Base URL

```
Development: http://localhost:8001
Production: https://api.yourdomain.com
```

### Authentication

**Status**: 🚧 To be implemented

```http
Authorization: Bearer <token>
```

### Common Response Formats

#### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

#### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }
  }
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, or DELETE |
| 201 | Created | Successful POST that creates a resource |
| 204 | No Content | Successful DELETE with no response body |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server-side error |

---

## REST Endpoints

### Health Check

#### `GET /health`

Check if the API is running.

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-10-16T12:00:00Z"
}
```

**Example**:
```bash
curl http://localhost:8001/health
```

---

### Example Endpoint

#### `POST /example`

**Description**: This is a placeholder for the first REST endpoint to be implemented in Phase 1, Sub-step 1.3.

**Status**: 🚧 To be implemented

**Request Body**:
```json
{
  "param1": "string",
  "param2": 42
}
```

**Response**: `201 Created`
```json
{
  "success": true,
  "data": {
    "id": "123",
    "param1": "string",
    "param2": 42,
    "created_at": "2025-10-16T12:00:00Z"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8001/example \
  -H "Content-Type: application/json" \
  -d '{"param1": "test", "param2": 42}'
```

**Error Responses**:
- `400`: Invalid input data
- `422`: Validation error

---

#### `GET /example/{id}`

**Description**: Retrieve a specific example resource.

**Status**: 🚧 To be implemented

**Parameters**:
- `id` (path, required): Resource identifier

**Response**: `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "123",
    "param1": "string",
    "param2": 42,
    "created_at": "2025-10-16T12:00:00Z"
  }
}
```

**Example**:
```bash
curl http://localhost:8001/example/123
```

**Error Responses**:
- `404`: Resource not found

---

#### `GET /example`

**Description**: List all example resources with pagination.

**Status**: 🚧 To be implemented

**Query Parameters**:
- `page` (optional, default: 1): Page number
- `limit` (optional, default: 20): Items per page
- `sort` (optional): Sort field
- `order` (optional, default: "asc"): Sort order ("asc" or "desc")

**Response**: `200 OK`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "123",
        "param1": "string",
        "param2": 42
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```

**Example**:
```bash
curl "http://localhost:8001/example?page=1&limit=20&sort=created_at&order=desc"
```

---

#### `PUT /example/{id}`

**Description**: Update an existing example resource.

**Status**: 🚧 To be implemented

**Parameters**:
- `id` (path, required): Resource identifier

**Request Body**:
```json
{
  "param1": "updated string",
  "param2": 99
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "123",
    "param1": "updated string",
    "param2": 99,
    "updated_at": "2025-10-16T13:00:00Z"
  }
}
```

**Example**:
```bash
curl -X PUT http://localhost:8001/example/123 \
  -H "Content-Type: application/json" \
  -d '{"param1": "updated", "param2": 99}'
```

**Error Responses**:
- `404`: Resource not found
- `422`: Validation error

---

#### `DELETE /example/{id}`

**Description**: Delete an example resource.

**Status**: 🚧 To be implemented

**Parameters**:
- `id` (path, required): Resource identifier

**Response**: `204 No Content`

**Example**:
```bash
curl -X DELETE http://localhost:8001/example/123
```

**Error Responses**:
- `404`: Resource not found

---

## REST Models

### Request Models

#### ExampleCreateRequest

```python
from pydantic import BaseModel, Field

class ExampleCreateRequest(BaseModel):
    param1: str = Field(..., min_length=1, max_length=100)
    param2: int = Field(..., ge=0, le=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "param1": "test value",
                "param2": 42
            }
        }
```

#### ExampleUpdateRequest

```python
from pydantic import BaseModel, Field

class ExampleUpdateRequest(BaseModel):
    param1: str | None = Field(None, min_length=1, max_length=100)
    param2: int | None = Field(None, ge=0, le=1000)
```

### Response Models

#### ExampleResponse

```python
from datetime import datetime
from pydantic import BaseModel

class ExampleResponse(BaseModel):
    id: str
    param1: str
    param2: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123",
                "param1": "test value",
                "param2": 42,
                "created_at": "2025-10-16T12:00:00Z",
                "updated_at": None
            }
        }
```

#### PaginatedResponse

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta
```

---

## Shared Business Logic

Both MCP and REST interfaces use the **same core business logic** located in `src/core/`. This ensures consistency across all interfaces.

### Example: How Interfaces Share Logic

#### Core Business Logic (`src/core/example.py`)

```python
from src.core.exceptions import ValidationError

def process_example(param1: str, param2: int) -> dict:
    """Core business logic for processing example data.

    This function is transport-agnostic and can be called by both
    MCP and REST interfaces.

    Args:
        param1: First parameter
        param2: Second parameter

    Returns:
        Processed result dictionary

    Raises:
        ValidationError: If validation fails
    """
    # Validation
    if not param1:
        raise ValidationError("param1 cannot be empty")
    if param2 < 0:
        raise ValidationError("param2 must be non-negative")

    # Business logic
    result = {
        "id": generate_id(),
        "param1": param1.upper(),
        "param2": param2 * 2,
        "processed": True
    }

    return result
```

#### MCP Interface (`src/mcp_server/tools.py`)

```python
from fastmcp import FastMCP
from src.core.example import process_example
from src.core.exceptions import ValidationError

mcp = FastMCP("example")

@mcp.tool()
def example_tool(param1: str, param2: int) -> dict:
    """MCP tool that uses core business logic."""
    try:
        result = process_example(param1, param2)
        return {"success": True, "result": result}
    except ValidationError as e:
        raise MCPError(code="VALIDATION_ERROR", message=str(e))
```

#### REST Interface (`src/rest_api/routes.py`)

```python
from fastapi import APIRouter, HTTPException
from src.core.example import process_example
from src.core.exceptions import ValidationError
from src.rest_api.models import ExampleCreateRequest, ExampleResponse

router = APIRouter()

@router.post("/example", status_code=201)
def create_example(request: ExampleCreateRequest) -> ExampleResponse:
    """REST endpoint that uses the same core business logic."""
    try:
        result = process_example(request.param1, request.param2)
        return ExampleResponse(**result)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Key Points

1. **Core logic is identical** - Both interfaces call `process_example()`
2. **Interfaces handle protocol specifics** - MCP returns MCP responses, REST returns HTTP responses
3. **Errors are translated** - `ValidationError` becomes `MCPError` or `HTTPException`
4. **Testing is efficient** - Test core logic once, gain confidence everywhere

---

## Interactive Documentation

### REST API Documentation

When the REST API server is running, you can access interactive documentation:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

### MCP Protocol Documentation

For MCP protocol details, see:
- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

---

## Development Status

This API reference will be updated as development progresses through the three phases:

- **Phase 1: Tools** 🚧 In Progress
  - Sub-step 1.1: STDIO ⏳ Planned
  - Sub-step 1.2: HTTP Streaming ⏳ Planned
  - Sub-step 1.3: REST API ⏳ Planned

- **Phase 2: Resources** ⏳ Planned
- **Phase 3: Prompts** ⏳ Planned

---

## Examples and Tutorials

### Complete Example: Creating and Retrieving Data

#### Via MCP (Python SDK)

```python
from mcp import MCPClient

# Connect to MCP server
async with MCPClient("http://localhost:8000/sse") as client:
    # Call tool to create data
    result = await client.call_tool(
        "example_tool",
        arguments={"param1": "test", "param2": 42}
    )
    print(f"Created: {result['result']['id']}")

    # Read resource
    resource = await client.read_resource(
        f"resource://example/{result['result']['id']}"
    )
    print(f"Retrieved: {resource}")
```

#### Via REST API (curl)

```bash
# Create data
RESPONSE=$(curl -X POST http://localhost:8001/example \
  -H "Content-Type: application/json" \
  -d '{"param1": "test", "param2": 42}')

ID=$(echo $RESPONSE | jq -r '.data.id')

# Retrieve data
curl http://localhost:8001/example/$ID
```

#### Via REST API (Python)

```python
import httpx

# Create data
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/example",
        json={"param1": "test", "param2": 42}
    )
    data = response.json()
    example_id = data["data"]["id"]

    # Retrieve data
    response = await client.get(f"http://localhost:8001/example/{example_id}")
    retrieved = response.json()
    print(retrieved)
```

---

## Support and Feedback

- 📖 [Architecture Documentation](ARCHITECTURE.md)
- 🛠️ [Setup Guide](SETUP.md)
- 🤝 [Contributing Guidelines](CONTRIBUTING.md)
- 🐛 [Report Issues](https://github.com/your-repo/issues)

---

**Last Updated**: October 16, 2025
**Version**: 0.1.0 (Development)

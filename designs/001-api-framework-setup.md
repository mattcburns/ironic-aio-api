# Design 001: API Framework Setup

**Status:** Implemented

## Overview

This design establishes the foundational architecture for the ironic-aio API sidecar. The key architectural decision is implementing a **service layer pattern** that allows both REST and MCP interfaces to share the same business logic, eliminating code duplication.

## Goals

1. Establish project structure that supports REST and MCP interfaces
2. Define the service layer pattern for shared business logic
3. Set up core dependencies with proper justification
4. Create configuration management
5. Implement basic health check endpoint as proof of concept

## Architecture Principles

### Stateless Design

This API is designed to be **completely stateless**:

- **Ironic is the source of truth**: All server state, operation status, and configuration is stored in Ironic
- **No local database**: The API does not maintain its own database or persistent storage
- **Pass-through operations**: The API wraps Ironic operations to simplify usage, but does not cache or store results
- **Horizontal scalability**: Multiple API instances can run without coordination
- **Resilience**: API restarts do not lose state; all state is reconstructable from Ironic

This stateless approach enables:
- Simple deployment and scaling
- Easy debugging (single source of truth)
- Future authentication can be added as a layer without state migration concerns

### Unified Single-Process Architecture

The API uses a **unified single-process architecture** where MCP is mounted as SSE (Server-Sent Events) endpoints within the FastAPI application. This provides:

- **Single container entrypoint**: One `uvicorn` command starts everything
- **Shared resources**: Both interfaces share the same service layer and connections
- **Simplified deployment**: No process manager or multiple ports needed

```
┌─────────────────────────────────────────┐
│           FastAPI Application           │
│         (Single uvicorn process)        │
├─────────────────┬───────────────────────┤
│   REST Routes   │   MCP SSE Endpoints   │
│   (/health,     │   (/mcp)              │
│    /servers)    │                       │
└────────┬────────┴───────────┬───────────┘
         │                    │
         └────────┬───────────┘
                  │
         ┌────────▼────────┐
         │  Service Layer  │
         │ (Business Logic)│
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  Ironic Client  │
         │ (OpenStack SDK) │
         └─────────────────┘
```

## Project Structure

```
api/
├── app.py                  # FastAPI application entry point (includes MCP)
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── README.md               # Documentation with dependency justifications
├── designs/                # Design documents
├── services/               # Business logic layer (shared)
│   ├── __init__.py
│   └── health.py           # Health check service (proof of concept)
├── routers/                # REST API route handlers
│   ├── __init__.py
│   └── health.py           # Health check routes
├── mcp_tools/              # MCP tool definitions (mounted via SSE in app.py)
│   ├── __init__.py
│   └── health.py           # Health check MCP tools
├── schemas/                # Pydantic models for request/response
│   ├── __init__.py
│   └── health.py           # Health check schemas
└── tests/                  # Test directory
    ├── __init__.py
    ├── conftest.py         # Pytest fixtures
    ├── test_health_service.py
    ├── test_health_router.py
    └── test_health_mcp.py
```

## Dependencies

The following dependencies are required (justifications in README.md):

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.109 | REST API framework with automatic OpenAPI generation |
| uvicorn | ^0.27 | ASGI server to run FastAPI |
| pydantic | ^2.0 | Data validation and settings management |
| mcp | ^1.0 | Model Context Protocol server implementation |
| httpx | ^0.27 | Async HTTP client (used by MCP, also useful for Ironic) |
| pydantic-settings | ^2.0 | Environment-based configuration |
| pytest | ^8.0 | Testing framework |
| pytest-asyncio | ^0.23 | Async test support |

## Implementation Details

### 1. Configuration (config.py)

```python
# Environment-based configuration using pydantic-settings
class Settings(BaseSettings):
    app_name: str = "ironic-aio-api"
    debug: bool = False
    ironic_api_url: str = "http://localhost:6385"
    ironic_api_version: str = "1.82"

    model_config = SettingsConfigDict(env_prefix="IRONIC_AIO_")
```

### 2. Service Layer Pattern

Services contain all business logic and are framework-agnostic:

```python
# services/health.py
class HealthService:
    """Health check service - shared by REST and MCP."""

    async def check_health(self) -> HealthStatus:
        """Check the health of the API and its dependencies."""
        # Business logic here
        return HealthStatus(status="healthy", ...)
```

### 3. REST Router

Routers are thin wrappers that call services:

```python
# routers/health.py
router = APIRouter(prefix="/health", tags=["health"])

@router.get("", response_model=HealthResponse)
async def get_health(service: HealthService = Depends(get_health_service)):
    return await service.check_health()
```

### 4. MCP Server Integration

The MCP server is created and mounted as SSE endpoints in app.py:

```python
# app.py
from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("ironic-aio")

# Import MCP tools (registers them with the mcp instance)
from mcp_tools import health  # noqa: F401

# Mount MCP SSE endpoints
app.mount("/mcp", mcp.sse_app())
```

### 5. MCP Tools

MCP tools are thin wrappers calling the same services:

```python
# mcp_tools/health.py
from app import mcp  # Import the shared MCP instance

@mcp.tool()
async def check_health() -> dict:
    """Check the health of the ironic-aio API."""
    service = get_health_service()
    result = await service.check_health()
    return result.model_dump()
```

### 6. Shared Schemas

Pydantic models are shared between REST and MCP:

```python
# schemas/health.py
class HealthStatus(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime
```

## OpenAPI Specification

The FastAPI application will auto-generate OpenAPI specs. Additional metadata:

- Title: "Ironic AIO API"
- Description: "Business process API for OpenStack Ironic operations"
- Version: "0.1.0"

## API Endpoints

The unified application exposes:

| Path | Purpose |
|------|---------|
| `/health` | REST health check endpoint |
| `/docs` | Swagger UI documentation |
| `/openapi.json` | OpenAPI specification |
| `/mcp` | MCP SSE endpoint for AI tool integration |

## Testing Requirements

1. **Unit tests for services**: Test business logic in isolation
2. **Integration tests for REST**: Test endpoints using FastAPI TestClient
3. **Integration tests for MCP**: Test MCP tools respond correctly
4. **Shared fixtures**: Common test data in conftest.py

## Acceptance Criteria

- [ ] Project structure created as specified
- [ ] All dependencies installed and documented in README.md
- [ ] Configuration management working with environment variables
- [ ] Health check service implemented
- [ ] Health check REST endpoint returns valid response at `/health`
- [ ] Health check MCP tool returns valid response via `/mcp`
- [ ] OpenAPI spec accessible at `/docs` and `/openapi.json`
- [ ] All tests pass with >80% coverage
- [ ] Single entrypoint `uvicorn app:app` starts both REST and MCP interfaces

## Documentation Requirements

The `api/README.md` must include:

1. **Development Setup**: Virtual environment creation and dependency installation
2. **Running the API**: Single command to start the unified server:
   ```bash
   # Start the API (serves both REST and MCP)
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
3. **Running Tests**: Include the following commands:
   ```bash
   # Run all tests
   pytest

   # Run with coverage (enforcing 80% minimum)
   pytest --cov=. --cov-report=term-missing --cov-fail-under=80

   # Run specific test file
   pytest tests/test_health_service.py

   # Run tests matching a pattern
   pytest -k "health"
   ```
4. **Dependency Justifications**: As required by AGENTS.md

**Note:** Once `api/README.md` is complete, update the root `AGENTS.md` to reference it for detailed development instructions (e.g., "See `api/README.md` for setup and testing commands").

## Future Designs

This design is intentionally minimal. Future designs will add:

- **002**: Ironic client integration and connection management
- **003**: Server discovery and listing business process
- **004**: Server provisioning workflow
- **005**: Server decommissioning workflow

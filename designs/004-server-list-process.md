# Design 004: Server List Business Process

**Status:** To Be Implemented

**Depends On:** Design 003

## Overview

This design implements the first business process: listing and discovering servers (Ironic nodes) with enriched information. This transforms raw Ironic node data into a business-friendly format with relevant metadata.

## Architecture Principles

### Stateless Design

The server listing workflow is stateless:

- **No local cache**: Every list/get request queries Ironic directly for current state
- **Real-time data**: Responses always reflect the current Ironic state, not cached data
- **Computed fields**: Business logic fields like `is_available` are computed on each request from Ironic node state
- **No aggregation tables**: Statistics are computed on-the-fly from Ironic data

## Goals

1. Create server listing service with filtering capabilities
2. Transform Ironic node data into business-friendly schema
3. Expose via REST endpoint and MCP tool
4. Support pagination for large inventories

## Implementation Note

**Ironic API calls should be left as stubs/TODOs.** Implement the full service structure, schemas, routers, and MCP tools, but leave the actual Ironic client method calls (e.g., listing nodes, getting node details) as TODO comments for manual implementation.

## Business Requirements

Internal customers need to:
- List all available servers
- Filter by provisioning state, resource class, or properties
- Get human-readable server information
- See server availability for provisioning

## Implementation Details

### 1. Server Schema (schemas/server.py)

```python
class ServerSummary(BaseModel):
    """Business-friendly server representation."""
    id: str
    name: str
    provision_state: str
    power_state: Optional[str]
    resource_class: Optional[str]
    is_available: bool  # Computed: can this server be provisioned?
    properties: dict    # Filtered subset of useful properties
    created_at: datetime
    updated_at: datetime

class ServerListResponse(BaseModel):
    servers: list[ServerSummary]
    total: int
    page: int
    page_size: int
```

### 2. Server Service (services/server.py)

```python
class ServerService:
    """Server management business logic."""

    def __init__(self, ironic_client: IronicClient):
        self.ironic = ironic_client

    async def list_servers(
        self,
        provision_state: Optional[str] = None,
        resource_class: Optional[str] = None,
        available_only: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> ServerListResponse:
        """List servers with optional filtering."""
        ...

    async def get_server(self, server_id: str) -> ServerSummary:
        """Get a single server by ID or name."""
        ...

    def _is_available(self, node: IronicNode) -> bool:
        """Determine if a node is available for provisioning."""
        # Business logic: available, not in maintenance, etc.
        ...
```

### 3. REST Router (routers/server.py)

```python
router = APIRouter(prefix="/servers", tags=["servers"])

@router.get("", response_model=ServerListResponse)
async def list_servers(
    provision_state: Optional[str] = None,
    resource_class: Optional[str] = None,
    available_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: ServerService = Depends(get_server_service)
):
    """List all servers with optional filtering."""
    return await service.list_servers(...)

@router.get("/{server_id}", response_model=ServerSummary)
async def get_server(
    server_id: str,
    service: ServerService = Depends(get_server_service)
):
    """Get a specific server by ID or name."""
    return await service.get_server(server_id)
```

### 4. MCP Tools (mcp_tools/server.py)

```python
from app import mcp  # Import the shared MCP instance

@mcp.tool()
async def list_servers(
    provision_state: Optional[str] = None,
    resource_class: Optional[str] = None,
    available_only: bool = False
) -> dict:
    """
    List all servers managed by Ironic.

    Args:
        provision_state: Filter by state (available, active, etc.)
        resource_class: Filter by resource class
        available_only: Only show servers available for provisioning

    Returns:
        List of servers with their current status
    """
    service = get_server_service()
    result = await service.list_servers(...)
    return result.model_dump()

@mcp.tool()
async def get_server(server_id: str) -> dict:
    """
    Get detailed information about a specific server.

    Args:
        server_id: The server ID or name

    Returns:
        Server details including provisioning state and properties
    """
    service = get_server_service()
    result = await service.get_server(server_id)
    return result.model_dump()
```

## Project Structure Additions

```
api/
├── services/
│   └── server.py
├── routers/
│   └── server.py
├── mcp_tools/
│   └── server.py
├── schemas/
│   └── server.py
└── tests/
    ├── test_server_service.py
    ├── test_server_router.py
    └── test_server_mcp.py
```

## Testing Requirements

1. Unit tests for ServerService with mocked IronicClient
2. Test filtering logic (provision_state, resource_class, available_only)
3. Test pagination
4. Test REST endpoints with TestClient
5. Test MCP tools return correct format

## Acceptance Criteria

- [ ] ServerService implemented with filtering and pagination
- [ ] REST endpoints accessible at /servers and /servers/{id}
- [ ] MCP tools list_servers and get_server working
- [ ] Business logic correctly determines server availability
- [ ] OpenAPI documentation includes all query parameters
- [ ] All tests pass

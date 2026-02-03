# Design 006: Server Unprovision Workflow

**Status:** To Be Implemented

**Depends On:** Design 004

## Overview

This design implements server unprovisioning (cleaning/decommissioning) - returning a provisioned server to an available state. This is the counterpart to the provisioning workflow.

## Architecture Principles

### Stateless Design

The unprovisioning workflow is stateless:

- **Ironic tracks all state**: Unprovision status is derived from Ironic's `provision_state` field
- **No operation database**: The "operation_id" is the Ironic node UUID; status is queried from Ironic
- **No cleanup orchestrator**: We trigger Ironic's cleaning process; Ironic handles the workflow
- **Idempotent status checks**: Status queries are read-only operations against Ironic

Operation tracking follows the same pattern as provisioning:
- `provision_state: cleaning` → status: "in_progress"
- `provision_state: available` → status: "completed"
- `provision_state: clean failed` → status: "failed"

## Goals

1. Implement server unprovisioning as an atomic business operation
2. Validate server is in correct state for unprovisioning
3. Support optional data wiping/cleaning configuration
4. Provide operation status tracking

## Implementation Note

**Ironic API calls should be left as stubs/TODOs.** Implement the full service structure, schemas, routers, and MCP tools, but leave the actual Ironic client method calls (e.g., triggering cleaning, querying unprovision state) as TODO comments for manual implementation.

## Business Requirements

Internal customers need to:
- Return servers they no longer need
- Optionally request secure data wiping
- Track unprovision progress
- Have servers automatically return to available pool

## Implementation Details

### 1. Unprovision Schema (schemas/unprovision.py)

```python
class UnprovisionRequest(BaseModel):
    """Request to unprovision a server."""
    server_id: str
    clean: bool = True  # Run cleaning steps

class UnprovisionResponse(BaseModel):
    """Unprovisioning operation result."""
    operation_id: str
    server_id: str
    server_name: str
    status: Literal["accepted", "in_progress", "completed", "failed"]
    message: str
    started_at: datetime
```

### 2. Unprovision Service (services/unprovision.py)

```python
class UnprovisionService:
    """Server unprovisioning business logic."""

    def __init__(self, ironic_client: IronicClient, server_service: ServerService):
        self.ironic = ironic_client
        self.server_service = server_service

    async def unprovision_server(self, request: UnprovisionRequest) -> UnprovisionResponse:
        """
        Initiate server unprovisioning.

        1. Validate server exists and is provisioned
        2. Trigger delete/clean via Ironic API
        3. Return operation tracking ID
        """
        ...

    async def get_unprovision_status(self, operation_id: str) -> UnprovisionStatus:
        """Get current status of an unprovisioning operation."""
        ...
```

### 3. REST Router (routers/unprovision.py)

```python
router = APIRouter(prefix="/unprovision", tags=["unprovisioning"])

@router.post("", response_model=UnprovisionResponse, status_code=202)
async def unprovision_server(
    request: UnprovisionRequest,
    service: UnprovisionService = Depends(get_unprovision_service)
):
    """
    Unprovision a server, returning it to available state.

    Returns 202 Accepted with operation ID for tracking.
    """
    return await service.unprovision_server(request)

@router.get("/{operation_id}", response_model=UnprovisionStatus)
async def get_unprovision_status(
    operation_id: str,
    service: UnprovisionService = Depends(get_unprovision_service)
):
    """Get the status of an unprovisioning operation."""
    return await service.get_unprovision_status(operation_id)
```

### 4. MCP Tools (mcp_tools/unprovision.py)

```python
from app import mcp  # Import the shared MCP instance

@mcp.tool()
async def unprovision_server(server_id: str, clean: bool = True) -> dict:
    """
    Unprovision a server, returning it to available state.

    Args:
        server_id: The server ID or name to unprovision
        clean: Whether to run cleaning/wiping steps (default: True)

    Returns:
        Operation details including ID for status tracking
    """
    ...

@mcp.tool()
async def check_unprovision_status(operation_id: str) -> dict:
    """
    Check the status of a server unprovisioning operation.

    Args:
        operation_id: The operation ID returned from unprovision_server

    Returns:
        Current unprovisioning status
    """
    ...
```

## Error Handling

| Error Condition | HTTP Status | Message |
|-----------------|-------------|---------|
| Server not found | 404 | "Server {id} not found" |
| Server not provisioned | 409 | "Server {id} is not in a provisionable state" |
| Ironic API error | 502 | "Failed to communicate with Ironic" |

## Project Structure Additions

```
api/
├── services/
│   └── unprovision.py
├── routers/
│   └── unprovision.py
├── mcp_tools/
│   └── unprovision.py
├── schemas/
│   └── unprovision.py
└── tests/
    ├── test_unprovision_service.py
    ├── test_unprovision_router.py
    └── test_unprovision_mcp.py
```

## Testing Requirements

1. Unit tests for UnprovisionService with mocked dependencies
2. Test validation (server exists, correct state)
3. Test REST endpoints return correct status codes
4. Test MCP tools

## Acceptance Criteria

- [ ] UnprovisionService implemented
- [ ] REST endpoint POST /unprovision returns 202 with operation ID
- [ ] REST endpoint GET /unprovision/{id} returns current status
- [ ] MCP tools unprovision_server and check_unprovision_status working
- [ ] Proper error handling with meaningful messages
- [ ] All tests pass

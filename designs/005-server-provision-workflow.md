# Design 005: Server Provision Workflow

**Status:** To Be Implemented

**Depends On:** Design 004

## Overview

This design implements the server provisioning business process - taking an available server through the complete provisioning workflow. This is a core business capability that orchestrates multiple Ironic API calls into a single, trackable operation.

## Architecture Principles

### Stateless Design

The provisioning workflow is stateless:

- **Ironic tracks all state**: Provisioning status is derived from Ironic's `provision_state` field
- **No operation database**: The "operation_id" is simply the Ironic node UUID; status is queried from Ironic
- **No workflow orchestrator**: We trigger Ironic's state machine; Ironic handles the provisioning workflow
- **Idempotent status checks**: Status queries are read-only operations against Ironic
- **No progress persistence**: Progress percentage is derived from Ironic's current provision_state

## Goals

1. Implement server provisioning as an atomic business operation
2. Validate server is available before provisioning
3. Support common provisioning parameters (image, network config)
4. Provide operation status tracking
5. Handle provisioning failures gracefully

## Implementation Note

**Ironic API calls should be left as stubs/TODOs.** Implement the full service structure, schemas, routers, and MCP tools, but leave the actual Ironic client method calls (e.g., setting deploy parameters, triggering provisioning, querying provision state) as TODO comments for manual implementation.

## Business Requirements

Internal customers need to:
- Request provisioning of a specific server or any available server matching criteria
- Specify the OS image and basic configuration
- Track provisioning progress
- Receive clear error messages on failure

## Implementation Details

### 1. Provision Schema (schemas/provision.py)

```python
class ProvisionRequest(BaseModel):
    """Request to provision a server."""
    server_id: Optional[str] = None  # Specific server, or None for auto-select
    resource_class: Optional[str] = None  # For auto-selection
    image_id: str  # Glance image ID or name
    config_drive: Optional[dict] = None  # Cloud-init user data

class ProvisionResponse(BaseModel):
    """Provisioning operation result."""
    operation_id: str  # UUID for tracking
    server_id: str
    server_name: str
    status: Literal["accepted", "in_progress", "completed", "failed"]
    message: str
    started_at: datetime

class ProvisionStatus(BaseModel):
    """Status of a provisioning operation."""
    operation_id: str
    server_id: str
    status: Literal["in_progress", "completed", "failed"]
    provision_state: str
    progress_percent: Optional[int]
    message: str
    started_at: datetime
    completed_at: Optional[datetime]
```

### 2. Provision Service (services/provision.py)

```python
class ProvisionService:
    """Server provisioning business logic."""

    def __init__(self, ironic_client: IronicClient, server_service: ServerService):
        self.ironic = ironic_client
        self.server_service = server_service

    async def provision_server(self, request: ProvisionRequest) -> ProvisionResponse:
        """
        Initiate server provisioning.

        1. Select server (specific or auto-select available)
        2. Validate server is in correct state
        3. Set deploy parameters (image, config)
        4. Trigger provisioning via Ironic API
        5. Return operation tracking ID
        """
        ...

    async def get_provision_status(self, operation_id: str) -> ProvisionStatus:
        """Get current status of a provisioning operation."""
        ...

    async def _select_server(self, request: ProvisionRequest) -> str:
        """Select a server for provisioning."""
        if request.server_id:
            return await self._validate_server_available(request.server_id)
        return await self._auto_select_server(request.resource_class)

    async def _validate_server_available(self, server_id: str) -> str:
        """Validate server exists and is available."""
        ...

    async def _auto_select_server(self, resource_class: Optional[str]) -> str:
        """Auto-select an available server matching criteria."""
        ...
```

### 3. REST Router (routers/provision.py)

```python
router = APIRouter(prefix="/provision", tags=["provisioning"])

@router.post("", response_model=ProvisionResponse, status_code=202)
async def provision_server(
    request: ProvisionRequest,
    service: ProvisionService = Depends(get_provision_service)
):
    """
    Provision a server with the specified image.

    Returns 202 Accepted with operation ID for tracking.
    """
    return await service.provision_server(request)

@router.get("/{operation_id}", response_model=ProvisionStatus)
async def get_provision_status(
    operation_id: str,
    service: ProvisionService = Depends(get_provision_service)
):
    """Get the status of a provisioning operation."""
    return await service.get_provision_status(operation_id)
```

### 4. MCP Tools (mcp_tools/provision.py)

```python
from app import mcp  # Import the shared MCP instance

@mcp.tool()
async def provision_server(
    image_id: str,
    server_id: Optional[str] = None,
    resource_class: Optional[str] = None
) -> dict:
    """
    Provision a server with an operating system image.

    Args:
        image_id: The OS image ID or name to deploy
        server_id: Specific server to provision (optional)
        resource_class: Auto-select server of this class if server_id not provided

    Returns:
        Operation details including ID for status tracking
    """
    service = get_provision_service()
    request = ProvisionRequest(
        server_id=server_id,
        resource_class=resource_class,
        image_id=image_id
    )
    result = await service.provision_server(request)
    return result.model_dump()

@mcp.tool()
async def check_provision_status(operation_id: str) -> dict:
    """
    Check the status of a server provisioning operation.

    Args:
        operation_id: The operation ID returned from provision_server

    Returns:
        Current provisioning status and progress
    """
    service = get_provision_service()
    result = await service.get_provision_status(operation_id)
    return result.model_dump()
```

## Operation Tracking

Operation tracking is **stateless** - the `operation_id` returned is the Ironic node UUID. Status is always derived from querying Ironic's current node state:

- `provision_state: deploying` → status: "in_progress"
- `provision_state: active` → status: "completed"
- `provision_state: deploy failed` → status: "failed"

This approach means:
- No local operation database required
- Status is always accurate (directly from Ironic)
- Multiple API instances return consistent results
- API restarts don't lose operation tracking

## Project Structure Additions

```
api/
├── services/
│   └── provision.py
├── routers/
│   └── provision.py
├── mcp_tools/
│   └── provision.py
├── schemas/
│   └── provision.py
└── tests/
    ├── test_provision_service.py
    ├── test_provision_router.py
    └── test_provision_mcp.py
```

## Error Handling

| Error Condition | HTTP Status | Message |
|-----------------|-------------|---------|
| Server not found | 404 | "Server {id} not found" |
| Server not available | 409 | "Server {id} is not available for provisioning" |
| No available servers | 404 | "No available servers matching criteria" |
| Image not found | 400 | "Image {id} not found" |
| Ironic API error | 502 | "Failed to communicate with Ironic" |

## Testing Requirements

1. Unit tests for ProvisionService with mocked dependencies
2. Test server selection logic (specific and auto-select)
3. Test validation failures
4. Test REST endpoints return correct status codes
5. Test MCP tools

## Acceptance Criteria

- [ ] ProvisionService implemented with server selection logic
- [ ] REST endpoint POST /provision returns 202 with operation ID
- [ ] REST endpoint GET /provision/{id} returns current status
- [ ] MCP tools provision_server and check_provision_status working
- [ ] Proper error handling with meaningful messages
- [ ] All tests pass

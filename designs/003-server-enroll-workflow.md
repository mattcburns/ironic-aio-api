# Design 003: Server Enroll Workflow

**Status:** To Be Implemented

**Depends On:** Design 002

## Overview

This design implements the server enrollment business process - adding new physical servers to Ironic management. Enrollment is the first step in the server lifecycle, allowing new hardware to be registered before it can be provisioned.

## Architecture Principles

### Stateless Design

The enrollment workflow is stateless:

- **No enrollment tracking table**: Ironic stores the enrolled node; we don't maintain a separate record
- **Idempotent validation**: BMC connectivity checks can be retried without side effects
- **Direct pass-through**: Enrollment creates the node in Ironic and returns the result immediately
- **No pending states**: There is no "pending enrollment" state in the API; nodes are either in Ironic or not

## Goals

1. Implement server enrollment as an atomic business operation
2. Support common BMC types (IPMI, Redfish, iLO, iDRAC)
3. Validate BMC connectivity during enrollment
4. Provide sensible defaults while allowing customization
5. Return enrolled server details

## Implementation Note

**Ironic API calls should be left as stubs/TODOs.** Implement the full service structure, schemas, routers, and MCP tools, but leave the actual Ironic client method calls (e.g., creating nodes, validating BMC connectivity) as TODO comments for manual implementation.

## Business Requirements

Internal customers need to:
- Register new physical servers with their BMC credentials
- Specify server properties (resource class, capabilities)
- Have BMC connectivity validated before enrollment completes
- Receive clear error messages on enrollment failures

## Implementation Details

### 1. Enroll Schema (schemas/enroll.py)

```python
class BMCCredentials(BaseModel):
    """BMC connection details."""
    driver: str = "ipmi"  # ipmi, redfish, ilo, idrac
    address: str  # BMC IP or hostname
    username: str
    password: str
    port: Optional[int] = None  # Default varies by driver

class EnrollRequest(BaseModel):
    """Request to enroll a new server."""
    name: str  # Unique server name
    bmc: BMCCredentials
    resource_class: Optional[str] = None  # e.g., "baremetal"
    properties: Optional[dict] = None  # CPU, memory, disk info
    validate_bmc: bool = True  # Test BMC connectivity

class EnrollResponse(BaseModel):
    """Enrollment operation result."""
    server_id: str  # UUID assigned by Ironic
    server_name: str
    status: Literal["enrolled", "failed"]
    provision_state: str
    message: str
    created_at: datetime
```

### 2. Enroll Service (services/enroll.py)

```python
class EnrollService:
    """Server enrollment business logic."""

    def __init__(self, ironic_client: IronicClient):
        self.ironic = ironic_client

    async def enroll_server(self, request: EnrollRequest) -> EnrollResponse:
        """
        Enroll a new server into Ironic.

        1. Validate name is unique
        2. Build driver_info from BMC credentials
        3. Create node in Ironic
        4. Optionally validate BMC connectivity
        5. Return enrollment result
        """
        ...

    async def _validate_name_unique(self, name: str) -> None:
        """Ensure server name doesn't already exist."""
        ...

    def _build_driver_info(self, bmc: BMCCredentials) -> dict:
        """Convert BMC credentials to Ironic driver_info format."""
        driver_map = {
            "ipmi": self._build_ipmi_driver_info,
            "redfish": self._build_redfish_driver_info,
        }
        builder = driver_map.get(bmc.driver, self._build_ipmi_driver_info)
        return builder(bmc)

    def _build_ipmi_driver_info(self, bmc: BMCCredentials) -> dict:
        """Build IPMI driver info."""
        return {
            "ipmi_address": bmc.address,
            "ipmi_username": bmc.username,
            "ipmi_password": bmc.password,
            "ipmi_port": bmc.port or 623,
        }

    def _build_redfish_driver_info(self, bmc: BMCCredentials) -> dict:
        """Build Redfish driver info."""
        return {
            "redfish_address": f"https://{bmc.address}",
            "redfish_username": bmc.username,
            "redfish_password": bmc.password,
            "redfish_system_id": "/redfish/v1/Systems/1",
        }

    async def _validate_bmc_connectivity(self, server_id: str) -> bool:
        """Validate BMC is reachable by attempting driver validation."""
        ...
```

### 3. REST Router (routers/enroll.py)

```python
router = APIRouter(prefix="/servers", tags=["servers"])

@router.post("", response_model=EnrollResponse, status_code=201)
async def enroll_server(
    request: EnrollRequest,
    service: EnrollService = Depends(get_enroll_service)
):
    """
    Enroll a new physical server into management.

    Registers the server's BMC credentials and creates an Ironic node.
    Returns 201 Created with the new server details.
    """
    return await service.enroll_server(request)
```

### 4. MCP Tools (mcp_tools/enroll.py)

```python
from app import mcp  # Import the shared MCP instance

@mcp.tool()
async def enroll_server(
    name: str,
    bmc_address: str,
    bmc_username: str,
    bmc_password: str,
    driver: str = "ipmi",
    resource_class: Optional[str] = None
) -> dict:
    """
    Enroll a new physical server into Ironic management.

    Args:
        name: Unique name for the server
        bmc_address: BMC IP address or hostname
        bmc_username: BMC username
        bmc_password: BMC password
        driver: BMC driver type (ipmi, redfish, ilo, idrac)
        resource_class: Optional resource classification

    Returns:
        Enrolled server details including assigned ID
    """
    service = get_enroll_service()
    request = EnrollRequest(
        name=name,
        bmc=BMCCredentials(
            driver=driver,
            address=bmc_address,
            username=bmc_username,
            password=bmc_password,
        ),
        resource_class=resource_class,
    )
    result = await service.enroll_server(request)
    return result.model_dump()
```

## Error Handling

| Error Condition | HTTP Status | Message |
|-----------------|-------------|---------|
| Name already exists | 409 | "Server with name '{name}' already exists" |
| Invalid driver | 400 | "Unsupported driver type: {driver}" |
| BMC validation failed | 422 | "Unable to connect to BMC at {address}" |
| Ironic API error | 502 | "Failed to communicate with Ironic" |

## Project Structure Additions

```
api/
├── services/
│   └── enroll.py
├── routers/
│   └── enroll.py
├── mcp_tools/
│   └── enroll.py
├── schemas/
│   └── enroll.py
└── tests/
    ├── test_enroll_service.py
    ├── test_enroll_router.py
    └── test_enroll_mcp.py
```

## Testing Requirements

1. Test successful enrollment with various drivers
2. Test name uniqueness validation
3. Test BMC connectivity validation (mocked)
4. Test error handling for invalid inputs
5. Test driver_info building for each supported driver

## Acceptance Criteria

- [ ] EnrollRequest and EnrollResponse schemas defined
- [ ] EnrollService implements enrollment logic
- [ ] REST POST /servers endpoint creates new servers
- [ ] MCP enroll_server tool available
- [ ] BMC connectivity validation works when requested
- [ ] Appropriate errors returned for invalid requests
- [ ] Unit tests cover service logic
- [ ] Integration tests verify REST endpoint
- [ ] MCP tool tests verify tool functionality

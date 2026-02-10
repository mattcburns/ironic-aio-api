# Design 011: Async Enrollment State Transitions

**Status:** Implemented

**Depends On:** Design 003

## Overview

This design implements an async-friendly enrollment pattern where enrollment is fast and non-blocking. Instead of waiting for long-running state transitions, enrollment completes when the node reaches "manageable" state. Providing (transitioning to "available") is a separate, user-initiated operation (see Design 015).

This design implements an async-friendly pattern where:
1. Enrollment transitions the node to "manage" state (synchronously - fast and required)
2. Enrollment returns immediately with the node in "manageable" state
3. Users then call a separate provide endpoint (Design 015) to make the node available for provisioning
4. A status endpoint allows clients to poll for transition completion
5. Users get immediate feedback on enrollment success with clear messaging about next steps

## Business Requirements

- Enrollment requests return quickly (within seconds), not minutes
- Clients can check the status of ongoing state transitions
- Clear messaging indicates when hardware cleaning is in progress
- API remains responsive and doesn't waste connection resources
- Follows the same pattern as server provisioning (Design 005)

## Architecture Patterns

### Stateless Design - No Local State Tracking

**Critical principle**: This API maintains NO local state about enrollments. All state lives in Ironic.

**What we DO:**
- Query Ironic for current node state on-demand
- Return what Ironic tells us in real-time
- Transform Ironic states into human-readable messages

**What we DON'T do:**
- Maintain enrollment status database/tables
- Track "in-progress" enrollments
- Store transition history or timestamps
- Cache node states
- Store operation IDs separate from Ironic node UUIDs

**Benefits:**
- No state synchronization issues between API and Ironic
- Service can restart without losing track of enrollments
- No database needed for enrollment tracking
- No state cleanup/garbage collection needed
- Ironic remains the single source of truth
- Multiple API instances can run without coordination
- No risk of stale state after service failures

### Non-Blocking State Transitions

State transitions are initiated but not awaited in the enrollment flow. This allows the HTTP response to return immediately while Ironic continues the operation asynchronously in the background.

**Key principle**: Do not block the API response waiting for long-running operations.

### Status Polling

Clients check enrollment status by polling a dedicated endpoint that queries Ironic for the current node state. This provides:
- Real-time status directly from Ironic (no cached/stale data)
- Stateless design (all state in Ironic)
- Ability to resume polling after network interruptions
- No server-side session or operation tracking

## Implementation Details

### 1. Update EnrollService Methods

#### `enroll_server()` - Synchronous manage transition only

Changes:
- Manage transition: Wait for completion (synchronous, returns immediately as it's quick)
- Return immediately with current provision_state in manageable
- Provide transition is now a separate operation (see Design 015)

```python
async def enroll_server(self, request: EnrollRequest) -> EnrollResponse:
    """
    Enroll a new server into Ironic.

    Manages the node and returns immediately. To make the node available for
    provisioning, call provide_server() afterward (see Design 015).
    """
    # ... node creation and port setup ...

    # Manage transition is synchronous (required, fast)
    logger.info(f"Transitioning node to manageable state for: {request.name}")
    try:
        node = await self.ironic.set_node_provision_state(server_id, "manage")
        provision_state = node.provision_state
        logger.info(f"Node transitioned to state: {provision_state}")
    except IronicClientError as e:
        logger.exception(f"Failed to transition node to manage: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to transition node to manage state: {str(e)}"
        )

    # Get current state from Ironic and return immediately
    current_node = await self.ironic.get_node(server_id)
    provision_state = current_node.provision_state

    return EnrollResponse(
        server_id=server_id,
        server_name=request.name,
        status="enrolled",
        provision_state=provision_state,
        message=f"Server '{request.name}' successfully enrolled and ready for management. "
                f"Current state: {provision_state}. "
                f"Call POST /servers/{server_id}/provide when ready to make available for provisioning.",
        created_at=datetime.now(timezone.utc)
    )
```

#### `get_enrollment_status(server_id)` - New method

Returns current enrollment status for a given server by querying Ironic directly.

**Important**: This is a pure query method - no state is stored or modified.

```python
async def get_enrollment_status(self, server_id: str) -> EnrollResponse:
    """
    Get current enrollment status of a server.

    Queries Ironic for the node's current state. No local state is maintained.
    This is a stateless query that can be called repeatedly to poll for completion.

    Args:
        server_id: UUID of the enrolled server (node ID in Ironic)

    Returns:
        EnrollResponse with current state from Ironic

    Raises:
        HTTPException: 404 if server not found
        HTTPException: 502 if Ironic API communication fails
    """
    try:
        # Query Ironic for current state (no local state)
        node = await self.ironic.get_node(server_id)

        # Map Ironic provision state to human-readable message (pure function)
        message = self._map_provision_state_to_message(node.provision_state)

        return EnrollResponse(
            server_id=node.id,
            server_name=node.name,
            status="enrolled",
            provision_state=node.provision_state,  # Direct from Ironic
            message=message,
            created_at=datetime.now(timezone.utc)  # Response generation time
        )
    except IronicClientError as e:
        logger.exception(f"Ironic API error getting enrollment status for {server_id}")
        raise HTTPException(
            status_code=502,
            detail=f"Ironic API error: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error getting enrollment status for {server_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error getting enrollment status: {str(e)}"
        )

def _map_provision_state_to_message(self, provision_state: str) -> str:
    """
    Map Ironic provision state to human-readable message.

    Pure function - no state modification.
    """
    state_messages = {
        "available": "Server is ready for provisioning",
        "manageable": "Server is being cleaned before becoming available",
        "manage": "Server is being cleaned before becoming available",
        "enroll": "Server enrolled, waiting to transition to manageable state",
        "cleaning": "Server hardware is being cleaned",
        "clean wait": "Server is waiting for cleaning to complete",
    }
    return state_messages.get(provision_state, f"Server status: {provision_state}")
```

### 2. Update EnrollRouter

Add status endpoint to check enrollment progress:

```python
@router.get("/{server_id}/enrollment-status", response_model=EnrollResponse)
async def get_enrollment_status(
    server_id: str,
    service: EnrollService = Depends(get_enroll_service)
) -> EnrollResponse:
    """
    Get current enrollment status of a server.

    Returns the server's current state from Ironic. Can be used to poll
    for completion of state transitions initiated during enrollment.

    This endpoint queries Ironic directly - no local state is maintained.
    Safe to call repeatedly for polling.

    Args:
        server_id: UUID of the enrolled server

    Returns:
        EnrollResponse with current server status from Ironic

    Raises:
        HTTPException: 404 if server not found in Ironic
        HTTPException: 502 if Ironic API communication fails
    """
    return await service.get_enrollment_status(server_id)
```

### 3. Update MCP Tool

Add status checking tool for enrollment:

```python
@mcp.tool()
async def get_enrollment_status(server_id: str) -> dict:
    """
    Get current enrollment status of a server.

    Queries Ironic for the node's current state. Use this to poll for completion
    of state transitions initiated during server enrollment. The server is fully
    ready when provision_state becomes 'available'.

    Args:
        server_id: UUID of the enrolled server

    Returns:
        Server enrollment status including current provision state from Ironic
    """
    service = get_enroll_service()
    result = await service.get_enrollment_status(server_id)
    return result.model_dump()
```

### 4. Update Tests

Test changes needed:

#### Service Tests (`test_enroll_service.py`)
- Update `test_enroll_server_success` to accept any valid provision state (not hardcoded "available")
- Add `test_enroll_server_transition_errors_dont_fail` - verify transition errors are logged but enrollment succeeds
- Add `test_get_enrollment_status_various_states` - test status method with different Ironic states
- Add `test_get_enrollment_status_not_found` - test 404 when server doesn't exist
- Update fake Ironic client to support mocking different provision states

#### Router Tests (`test_enroll_router.py`)
- Add `test_get_enrollment_status_endpoint` - test new GET endpoint
- Add `test_get_enrollment_status_not_found` - test 404 handling
- Add `test_get_enrollment_status_ironic_error` - test 502 handling

#### MCP Tests (`test_enroll_mcp.py`)
- Add `test_get_enrollment_status_mcp_tool` - test new MCP tool

## Client Usage Pattern

### Initial Enrollment
```python
# POST /servers - Returns quickly (seconds, not minutes)
response = client.post("/servers", json=enroll_request)
server_id = response.json()["server_id"]
provision_state = response.json()["provision_state"]
print(f"Enrolled: {provision_state}")
# Output: "Enrolled: enroll" or "Enrolled: manageable"
```

### Poll for Transition Completion
```python
import time

# Poll until available
while True:
    status = client.get(f"/servers/{server_id}/enrollment-status")
    state = status.json()["provision_state"]
    message = status.json()["message"]
    print(f"{state}: {message}")

    if state == "available":
        print("Server ready for provisioning")
        break

    time.sleep(10)  # Poll every 10 seconds (use exponential backoff in production)
```

### Recommended Polling Strategy
```python
import time

def wait_for_available(client, server_id, max_wait_minutes=30, initial_delay=5):
    """
    Poll for server to become available with exponential backoff.
    """
    delay = initial_delay
    max_delay = 60
    elapsed = 0

    while elapsed < max_wait_minutes * 60:
        status = client.get(f"/servers/{server_id}/enrollment-status")
        state = status.json()["provision_state"]

        if state == "available":
            return True

        time.sleep(delay)
        elapsed += delay
        delay = min(delay * 1.5, max_delay)  # Exponential backoff with cap

    return False  # Timeout
```

## Error Handling

### Transition Failures

If a state transition fails (e.g., BMC unreachable during manage transition):
- Log the error at WARNING level
- Don't fail the enrollment (node was successfully created)
- Return the current state in response
- Client can check status endpoint later or investigate logs

**Rationale**: The node is successfully created and available in Ironic even if transitions fail. Users can:
- Retry transitions manually via Ironic
- Delete and re-enroll if needed
- Debug BMC connectivity issues

### Network/Connectivity Issues

If the client's status polling request fails:
- Standard HTTP error handling applies (502, timeout, etc.)
- Retrying the status endpoint is safe (idempotent, read-only)
- No state is modified by status checks
- Client can resume polling from any point

### Service Restarts

If the API service restarts during enrollment:
- **No impact** - no local state is lost because we don't maintain any
- Clients can continue polling the status endpoint
- All state is preserved in Ironic

## Testing Requirements

- [ ] Service method `get_enrollment_status()` returns current Ironic state
- [ ] Enrollment doesn't wait for transitions to complete
- [ ] Transition errors don't fail enrollment (logged as warnings)
- [ ] Router GET `/servers/{id}/enrollment-status` endpoint works
- [ ] Router endpoint handles missing servers (404) correctly
- [ ] Router endpoint handles Ironic API errors (502) correctly
- [ ] MCP tool provides access to status checking
- [ ] Status method can be called multiple times (idempotent)
- [ ] Response message clearly indicates transitions are ongoing
- [ ] Fake Ironic client supports different provision states for testing

## Acceptance Criteria

- [ ] `enroll_server()` returns within ~5 seconds regardless of provide transition duration
- [ ] Manage transition is synchronous and blocks until completion
- [ ] Provide transition is asynchronous and doesn't block response
- [ ] Provide transition errors are logged but don't fail enrollment
- [ ] New `get_enrollment_status()` service method implemented
- [ ] New GET `/servers/{id}/enrollment-status` endpoint available
- [ ] New `get_enrollment_status()` MCP tool available
- [ ] Response includes current provision_state from manage transition
- [ ] Response message includes URL to status endpoint
- [ ] All tests pass with async provide pattern
- [ ] No local state is maintained (all queries go to Ironic)

## Migration Notes

This is a **breaking change** for API clients that expect `provision_state` to be "available" immediately after enrollment.

### Migration Steps for Clients

1. **Update expectations**: After POST `/servers`, check the returned `provision_state`
2. **Implement polling**: If you need to wait for "available" state, poll GET `/servers/{id}/enrollment-status`
3. **Use exponential backoff**: Don't poll too frequently (recommend 5-10 second initial delay)
4. **Handle timeouts**: Cleaning can take 5-15 minutes depending on hardware

### Example Migration

**Before (blocked on enrollment):**
```python
response = client.post("/servers", json=enroll_request)
assert response.json()["provision_state"] == "available"  # BREAKS
```

**After (poll for completion):**
```python
response = client.post("/servers", json=enroll_request)
server_id = response.json()["server_id"]

# Poll until available
while True:
    status = client.get(f"/servers/{server_id}/enrollment-status")
    if status.json()["provision_state"] == "available":
        break
    time.sleep(10)
```

## Related Designs

- Design 003: Server Enroll Workflow (initial implementation - now uses async transitions)
- Design 005: Server Provision Workflow (provides pattern for async operations and status polling)
- Design 006: Server Unprovision Workflow (also uses async pattern with status endpoint)

## Project Structure Changes

```
api/
├── services/
│   └── enroll.py (modified)
│       - enroll_server(): add try-except for transitions, get current state
│       - get_enrollment_status(): NEW method
│       - _map_provision_state_to_message(): NEW helper
├── routers/
│   └── enroll.py (modified)
│       - GET /{server_id}/enrollment-status: NEW endpoint
├── mcp_tools/
│   └── enroll.py (modified)
│       - get_enrollment_status(): NEW tool
└── tests/
    ├── test_enroll_service.py (modified)
    │   - Update existing tests
    │   - Add status method tests
    ├── test_enroll_router.py (modified)
    │   - Add status endpoint tests
    └── test_enroll_mcp.py (modified)
        - Add status tool tests
```

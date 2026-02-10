# Design 015: Explicit Provide Workflow

**Status:** implemented

**Depends On:** Design 011, Design 002

## Overview

The enrollment process is now a two-stage asynchronous workflow: **manage** (enrollment) and **provide** (availability). Both transitions occur asynchronously in Ironic with the API returning 202 Accepted immediately. This gives operators precise control over when servers become available for provisioning.

**Key characteristics:**
- Enrollment (manage transition) initiates asynchronously and returns 202 Accepted
- A separate `/servers/{server_id}/provide` endpoint triggers the provide transition
- Both transitions are non-blocking; Ironic processes them in background
- Operators must poll `/servers/{server_id}/enrollment-status` to track transition progress
- Status remains queryable via the existing `/servers/{server_id}/enrollment-status` endpoint

## Goals

1. Make both enrollment (manage) and availability (provide) fully asynchronous
2. Return 202 Accepted for both transitions (RFC 7231: accepted for processing)
3. Give operators explicit control over when nodes transition
4. Allow batch operations (enroll many, provide selectively)
5. Require status polling for progress tracking (preventing timeout issues)
6. Maintain single source of truth (Ironic state)

## Non-Goals

- No new persistence layer
- No background job scheduling
- No state tracking outside Ironic

## Implementation Details

### 1) New EnrollService.provide_server Method

```python
async def provide_server(self, server_id: str) -> EnrollResponse:
    """
    Transition a managed server to available state for provisioning.

    Call this after enrollment when the server is ready to join the available pool.
    The node must be in 'manageable' state to proceed.

    Args:
        server_id: UUID or name of the server

    Returns:
        EnrollResponse with updated status

    Raises:
        HTTPException: 404 if server not found
        HTTPException: 400 if server is not in manageable state
        HTTPException: 502 if Ironic API communication fails
    """
    try:
        # Fetch current node to check state
        node = await self.ironic.get_node(server_id, ignore_missing=True)

        if node is None:
            raise HTTPException(
                status_code=404,
                detail=f"Server '{server_id}' not found"
            )

        current_state = node.provision_state
        if current_state != "manageable":
            raise HTTPException(
                status_code=400,
                detail=f"Server must be in 'manageable' state to provide. "
                       f"Current state: {current_state}"
            )

        logger.info(f"Initiating provide transition for server: {server_id}")

        # Initiate transition to provide (asynchronous)
        await self.ironic.set_node_provision_state(server_id, "provide")

        logger.info(f"Provide transition initiated for server: {server_id}")

        # Get current state and return
        current_node = await self.ironic.get_node(server_id)
        provision_state = current_node.provision_state

        return EnrollResponse(
            server_id=server_id,
            server_name=getattr(current_node, "name", "unknown"),
            status="enrolled",
            provision_state=provision_state,
            message=f"Server transition to available initiated. "
                    f"Current state: {provision_state}. "
                    f"Hardware cleaning may take several minutes. "
                    f"Use GET /servers/{server_id}/enrollment-status to check progress.",
            created_at=datetime.now(timezone.utc)
        )

    except HTTPException:
        raise
    except IronicClientError as e:
        logger.exception(f"Ironic API error during provide for {server_id}")
        raise HTTPException(
            status_code=502,
            detail=f"Ironic API error: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error during provide for {server_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during provide: {str(e)}"
        )
```

### 2) EnrollService.enroll_server Changes

Remove the blocking behavior from enrollment:
- Manage transition is asynchronous (initiated, not waited for)
- Return response immediately with early provision state
- Document that `provide_server` should be called when ready

```python
# Manage transition is asynchronous (initiated, returns immediately)
logger.info(f"Transitioning node to manageable state for: {request.name}")
try:
    await self.ironic.set_node_provision_state(server_id, "manage")
except IronicClientError as e:
    logger.exception(f"Failed to initiate manage transition: {str(e)}")
    raise HTTPException(
        status_code=502,
        detail=f"Failed to initiate manage transition: {str(e)}"
    )

# Get current state and return immediately (202 Accepted)
current_node = await self.ironic.get_node(server_id)
provision_state = current_node.provision_state

logger.info(f"Enrollment initiated for: {request.name}")
return EnrollResponse(
    server_id=server_id,
    server_name=request.name,
    status="enrolled",
    provision_state=provision_state,
    message=f"Server '{request.name}' enrollment initiated. "
            f"Current state: {provision_state}. "
            f"Management state transition is in progress. "
            f"Use GET /servers/{server_id}/enrollment-status to check progress. "
            f"Call POST /servers/{server_id}/provide when ready to make available for provisioning.",
    created_at=datetime.now(timezone.utc)
)```

### 3) Router Endpoint

Both endpoints return 202 Accepted to indicate asynchronous processing:

```python
@router.post("", response_model=EnrollResponse, status_code=202)
async def enroll_server(
    request: EnrollRequest,
    service: EnrollService = Depends(get_enroll_service)
) -> EnrollResponse:
    """
    Enroll a new physical server into management.

    Initiates asynchronous management state transition. Returns 202 Accepted.
    Use GET /servers/{server_id}/enrollment-status to track progress.

    Args:
        request: Enrollment request containing server details
        service: Enrollment service dependency

    Returns:
        EnrollResponse with early provision state

    Raises:
        HTTPException: 409 if server name already exists
        HTTPException: 400 if driver type is invalid
        HTTPException: 422 if BMC validation fails
        HTTPException: 502 if Ironic API communication fails
    """
    return await service.enroll_server(request)

@router.post("/{server_id}/provide", response_model=EnrollResponse, status_code=202)
async def provide_server(
    server_id: str,
    service: EnrollService = Depends(get_enroll_service)
) -> EnrollResponse:
    """
    Transition a managed server to available state for provisioning.

    Initiates asynchronous provide state transition. Returns 202 Accepted.
    Hardware cleaning is performed asynchronously and may take several minutes.
    Use GET /servers/{server_id}/enrollment-status to track progress.

    Args:
        server_id: UUID or name of the server
        service: Enrollment service dependency

    Returns:
        EnrollResponse with updated status

    Raises:
        HTTPException: 404 if server not found
        HTTPException: 400 if server is not in manageable state
        HTTPException: 502 if Ironic API communication fails
    """
    return await service.provide_server(server_id)
```

### 4) New MCP Tool

Add MCP tool for provide operation:

```python
@mcp.tool()
async def provide_server(server_id: str) -> dict:
    """
    Transition a managed server to available state for provisioning.

    Call this after enrollment when the server has completed initial setup
    and is ready to join the available pool.

    Args:
        server_id: UUID or name of the server

    Returns:
        Server status with updated provision state
    """
    service = get_enroll_service()
    result = await service.provide_server(server_id)
    return result.model_dump()
```

## Test Updates

### Unit Tests

Update [tests/test_enroll_service.py](tests/test_enroll_service.py):
- Remove tests for provide during enrollment
- Add tests for `provide_server` method:
  - Success case: node in manageable transitions
  - Error: node not in manageable state (400)
  - Error: node not found (404)
  - Error: Ironic API failure (502)
- Update enrollment tests to verify no provide is called

### Router Tests

Update [tests/test_enroll_router.py](tests/test_enroll_router.py):
- Remove provide assertions from enrollment flow
- Add tests for POST `/servers/{server_id}/provide` endpoint:
  - Success returns 202 (Accepted)
  - Validates response schema
  - Error handling

### MCP Tests

Update [tests/test_enroll_mcp.py](tests/test_enroll_mcp.py):
- Add test for `provide_server` MCP tool
- Verify it calls the service correctly

## Acceptance Criteria

- ✅ Enrollment endpoint returns 202 Accepted (asynchronous processing)
- ✅ Manage transition is non-blocking; returns immediately with early provision state
- ✅ New `POST /servers/{server_id}/provide` endpoint returns 202 Accepted
- ✅ Provide can only be called on manageable servers (400 if not)
- ✅ Both endpoints return helpful messages directing users to status endpoint
- ✅ Tests verify 202 responses for both enrollment and provide
- ✅ Complete test coverage: success, not found, invalid state, API errors
- ✅ Both REST and MCP APIs support enrollment and provide operations
- ✅ Status endpoint available for polling progress on both transitions

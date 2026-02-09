# Design 014: Ironic Unprovisioning Integration

**Status:** to be implemented

**Depends On:** Design 006, Design 002, Design 012

## Overview

Unprovisioning currently returns a mock response and does not trigger Ironic state changes. This design implements the real unprovisioning flow and live status checks backed by Ironic.

## Goals

1. Trigger the correct Ironic unprovisioning transition.
2. Provide real-time status based on Ironic state.
3. Update tests to cover real Ironic calls and status mapping.

## Non-Goals

- No persistence of unprovision operations outside Ironic.
- No new dependencies.

## Implementation Details

### 1) UnprovisionService.unprovision_server

Replace TODO with real Ironic call:

- If `request.clean` is `True`, set target to `"deleted"`.
- If `request.clean` is `False`, set target to `"available"`.

Flow:

1. Get server details (`_get_server_by_id`).
2. Validate current `provision_state` is in the allowed set.
3. Call `ironic.set_node_provision_state(server.id, target_state)`.
4. Return `UnprovisionResponse` with status `accepted`.

Map Ironic failures to `HTTPException(502)`.

### 2) UnprovisionService.get_unprovision_status

Implement real status retrieval:

- Fetch node via `ironic.get_node(operation_id, ignore_missing=True)`.
- If missing, return `HTTPException(404)`.
- Map `node.provision_state` to status:
  - `cleaning`, `deleting` -> `in_progress`
  - `available` -> `completed`
  - `clean failed`, `error` -> `failed`
- Provide a progress estimate map (optional but deterministic).
- Set `completed_at` when status is `completed` or `failed`.

### 3) Error Handling

- `HTTPException(404)`: node not found.
- `HTTPException(502)`: Ironic client failures.

## Test Updates

### Unit Tests

- Update [tests/test_unprovision_service.py](tests/test_unprovision_service.py):
  - Use `AsyncMock` for `set_node_provision_state` and `get_node`.
  - Assert expected calls and error handling.
  - Add tests for status mapping.

### Router and MCP Tests

- Update router and MCP tests to validate real responses without `NotImplementedError`.

## Acceptance Criteria

- Unprovision triggers Ironic with the correct target state.
- Status polling uses real Ironic state.
- Tests cover success, not found, and failure paths.

# Design 013: Ironic Provisioning Integration

**Status:** implemented

**Depends On:** Design 005, Design 002, Design 012

## Overview

Provisioning currently stops at server selection and returns a mock status response. This design implements the real Ironic provisioning flow, including instance info configuration, state transition to `active`, and live status queries.

Provisioning remains stateless: the API initiates the workflow and returns `202 Accepted`, and clients poll for progress via a status endpoint backed by Ironic.

## Goals

1. Apply deployment parameters to the Ironic node.
2. Trigger the Ironic provisioning workflow.
3. Implement status polling backed by Ironic state.
4. Update tests to validate Ironic client calls and status mapping.

## Non-Goals

- No long-running background workers.
- No persistence of operation status outside Ironic.

## Implementation Details

### 1) Ironic Client Extensions

Add a method to set instance info for a node:

- `set_node_instance_info(node_id: str, instance_info: dict) -> Node`
- Implementation should prefer the SDK helper if present, or fall back to `update_node` with a patch to `/instance_info`.

Extend `set_node_provision_state` to accept an optional `configdrive` argument and pass it through to the SDK call.

### 2) ProvisionService.provision_server

Replace TODOs with real calls:

- Build `instance_info` with at least:
  - `image_source`: `request.image_source`
  - `image_checksum`: `request.image_checksum` (when provided)
- If `request.config_drive` is provided:
  - Serialize to JSON with `json.dumps`.
  - Base64-encode the JSON string.
  - Pass as `configdrive` to `set_node_provision_state`.

Flow:

1. Select server (`_select_server`).
2. Resolve server details (`_get_server_by_id`).
3. Call `ironic.set_node_instance_info(server_id, instance_info)`.
4. Call `ironic.set_node_provision_state(server_id, "active", configdrive=...)`.
5. Return `ProvisionResponse` with status `accepted`.

Errors from the Ironic client should map to `HTTPException(502)`.

### 3) ProvisionService.get_provision_status

Implement real status retrieval:

- Fetch node via `ironic.get_node(operation_id, ignore_missing=True)`.
- If missing, return `HTTPException(404)`.
- Map `node.provision_state` to status:
  - `deploying`, `cleaning`, `manageable`, `available` -> `in_progress`
  - `active` -> `completed`
  - `deploy failed`, `error` -> `failed`
- Provide a progress estimate map (optional but deterministic).
- Set `completed_at` when status is `completed` or `failed`.

### 4) Error Handling

- `HTTPException(404)`: node not found.
- `HTTPException(502)`: Ironic client failures.

## Test Updates

### Unit Tests

- Update [tests/test_provision_service.py](tests/test_provision_service.py):
  - Use `AsyncMock` for `set_node_instance_info` and `set_node_provision_state`.
  - Assert calls are made with expected parameters.
  - Add tests for `get_provision_status` mapping with mocked nodes.

### Router and MCP Tests

- Update router and MCP tests to validate real responses without `NotImplementedError`.

## Acceptance Criteria

- Instance info is configured before provisioning.
- Ironic provisioning is triggered with target `active`.
- Status polling uses real Ironic state.
- Tests cover success and failure paths.

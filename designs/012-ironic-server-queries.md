# Design 012: Ironic Server Query Integration

**Status:** implemented

**Depends On:** Design 004, Design 002

## Overview

The server list and server detail endpoints currently return mock data and raise `NotImplementedError` for lookups. This design implements the real Ironic-backed query flow for server listing, filtering, and detail retrieval.

## Goals

1. Use Ironic data as the single source of truth for server list and detail views.
2. Implement consistent filtering and pagination in `ServerService`.
3. Convert Ironic node data to `ServerSummary` reliably.
4. Update tests to reflect real Ironic-backed behavior.

## Non-Goals

- No caching or persistence layer.
- No new external dependencies.

## Implementation Details

### 1) ServerService.list_servers

- Call `IronicClient.list_nodes()` to retrieve all nodes.
- Apply filters in-memory:
  - `provision_state`: keep nodes whose `provision_state` matches.
  - `resource_class`: keep nodes whose `resource_class` matches.
  - `available_only`: keep nodes where `_is_available(node)` returns `True`.
- Map nodes to `ServerSummary` via `_node_to_summary`.
- Apply pagination after filtering.

### 2) ServerService.get_server

- Fetch the node by ID or name.
- If the node is missing, raise `HTTPException(status_code=404)` with a clear message.
- Convert to `ServerSummary` using `_node_to_summary`.
- Wrap Ironic failures as `HTTPException(status_code=502)`.

To support a missing node response, update `IronicClient.get_node` to accept an `ignore_missing: bool = True` parameter. When `ignore_missing` is `True`, call the SDK with `ignore_missing=True` and return `None` if the node does not exist.

### 3) Availability Logic

Implement `_is_available(node)` with the business rules:

- `node.provision_state == "available"`
- `node.maintenance` is `False`
- `node.power_state == "power off"`

If any field is missing, treat the node as not available.

### 4) Node Mapping

Implement `_node_to_summary(node)`:

- `id` uses `node.id` if present, else `node.uuid`.
- `name` uses `node.name`.
- `provision_state`, `power_state`, `resource_class`, and `properties` copy directly.
- `is_available` uses `_is_available(node)`.
- `created_at` and `updated_at`:
  - If the SDK values are `datetime`, use as-is.
  - If they are strings, parse with `datetime.fromisoformat`.
  - If missing, default to `datetime.now(timezone.utc)`.

### 5) Error Handling

- Wrap any `IronicClientError` in a `502` response.
- For not found, return `404`.

## Test Updates

### Unit Tests

- Update [tests/test_server_service.py](tests/test_server_service.py) to assert real behavior:
  - `list_servers` returns data from the fake client.
  - Filtering and pagination produce expected counts.
  - `get_server` returns a `ServerSummary` for existing nodes.
  - `get_server` raises `HTTPException(404)` for missing nodes.

### Router Tests

- Update [tests/test_server_router.py](tests/test_server_router.py) to expect HTTP responses instead of `NotImplementedError`.
- For GET `/servers/{id}`, validate the response schema for a mocked server or adjust to use dependency overrides.

## Acceptance Criteria

- `ServerService.list_servers` uses Ironic nodes and applies filters and pagination.
- `ServerService.get_server` returns a `ServerSummary` or a `404`.
- Availability logic matches business rules.
- Node mapping handles timestamps reliably.
- Tests are updated and pass.

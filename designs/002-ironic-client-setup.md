# Design 002: Ironic Client Setup

**Status:** Implemented

**Depends On:** Design 001

## Overview

This design adds the OpenStack Ironic client integration, establishing the foundation for all Ironic API interactions. It creates a reusable client wrapper that handles authentication, connection management, and common Ironic operations.

## Architecture Principles

### Stateless Design

The Ironic client wrapper follows the stateless architecture:

- **No connection caching**: Connections are created per-request or use lightweight pooling without local state
- **Ironic is the source of truth**: All queries go directly to Ironic; no local caching of node data
- **Idempotent operations**: Client methods can be safely retried without side effects
- **No operation tracking**: The client does not maintain operation history; Ironic tracks node state transitions

## Goals

1. Create a reusable Ironic client wrapper
2. Handle noauth authentication for standalone Ironic
3. Implement connection pooling and error handling
4. Add Ironic connectivity to health checks
5. Provide async-compatible interface

## Implementation Note

**Ironic API calls should be left as stubs/TODOs.** The implementer should create the client class structure, method signatures, and error handling framework, but leave the actual Ironic SDK calls as TODO comments for manual implementation. This allows the project owner to write the specific Ironic interaction logic themselves.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| openstacksdk | ^3.0 | Official OpenStack SDK for Ironic API |

## Implementation Details

### 1. Client Wrapper (clients/ironic.py)

```python
class IronicClient:
    """Wrapper around OpenStack SDK for Ironic operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._connection = None

    async def get_connection(self) -> Connection:
        """Get or create OpenStack connection."""
        ...

    async def list_nodes(self) -> list[Node]:
        """List all Ironic nodes."""
        ...

    async def get_node(self, node_id: str) -> Node:
        """Get a specific node by ID or name."""
        ...

    async def check_connectivity(self) -> bool:
        """Check if Ironic API is reachable."""
        ...
```

### 2. Configuration Updates

Add to Settings:
- `ironic_api_url`: Ironic API endpoint (default: "http://localhost:6385")
- `ironic_api_version`: Ironic API microversion (default: "1.82")

### 3. Health Check Enhancement

Update HealthService to include Ironic connectivity status:

```python
class HealthStatus(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime
    ironic_connected: bool
    ironic_api_version: Optional[str]
```

### 4. Dependency Injection

```python
# dependencies.py
def get_ironic_client() -> IronicClient:
    return IronicClient(get_settings())
```

## Project Structure Additions

```
api/
├── clients/
│   ├── __init__.py
│   └── ironic.py           # Ironic client wrapper
└── tests/
    └── test_ironic_client.py
```

## Testing Requirements

1. Mock OpenStack SDK for unit tests
2. Test noauth connection setup
3. Test error handling for connection failures
4. Test health check with Ironic status

## Acceptance Criteria

- [ ] IronicClient class implemented with async support
- [ ] Noauth authentication configured for standalone Ironic
- [ ] Health check includes Ironic connectivity status
- [ ] Proper error handling for connection failures
- [ ] All tests pass with mocked Ironic API
- [ ] README.md updated with openstacksdk justification

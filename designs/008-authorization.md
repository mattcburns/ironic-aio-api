# Design 008: Authorization

**Status:** To Be Implemented

**Depends On:** Design 007

## Overview

This design adds authorization to control what authenticated users can do. It leverages JWT claims for role-based access control and Ironic's built-in ownership fields for resource-based access control.

## Architecture Principles

### Stateless Design

Authorization remains stateless:

- **Roles from JWT claims**: No local role database; roles embedded in tokens
- **Ownership from Ironic**: Resource ownership uses Ironic's `owner` and `lessee` fields
- **No policy database**: Authorization rules are code-defined, not stored
- **Cacheless evaluation**: Each request evaluates permissions from token + Ironic state

## Goals

1. Implement role-based access control (RBAC) using JWT claims
2. Implement resource-based access control using Ironic ownership
3. Define clear permission model for API operations
4. Maintain backward compatibility when auth is disabled

## Implementation Note

**Ironic API calls should be left as stubs/TODOs.** Implement the full authorization framework, but leave the actual Ironic client method calls (e.g., fetching node ownership/lessee fields) as TODO comments for manual implementation.

## Business Requirements

- Admins can manage all servers
- Users can only manage servers they own or are leased to them
- Service accounts have configurable permissions
- Clear audit trail of who did what (see Design 009)

## Permission Model

| Role | List Servers | View Server | Enroll | Provision | Unprovision |
|------|--------------|-------------|--------|-----------|-------------|
| admin | All | All | Yes | All | All |
| operator | All | All | Yes | Owned/Leased | Owned/Leased |
| user | Owned/Leased | Owned/Leased | No | Owned/Leased | Owned/Leased |
| readonly | All | All | No | No | No |

## Implementation Details

### 1. Authorization Schema (schemas/auth.py additions)

```python
class Permission(str, Enum):
    """API permissions."""
    SERVER_LIST = "server:list"
    SERVER_READ = "server:read"
    SERVER_ENROLL = "server:enroll"
    SERVER_PROVISION = "server:provision"
    SERVER_UNPROVISION = "server:unprovision"

# Role to permissions mapping
ROLE_PERMISSIONS = {
    "admin": {Permission.SERVER_LIST, Permission.SERVER_READ, Permission.SERVER_ENROLL,
              Permission.SERVER_PROVISION, Permission.SERVER_UNPROVISION},
    "operator": {Permission.SERVER_LIST, Permission.SERVER_READ, Permission.SERVER_ENROLL,
                 Permission.SERVER_PROVISION, Permission.SERVER_UNPROVISION},
    "user": {Permission.SERVER_LIST, Permission.SERVER_READ,
             Permission.SERVER_PROVISION, Permission.SERVER_UNPROVISION},
    "readonly": {Permission.SERVER_LIST, Permission.SERVER_READ},
}
```

### 2. Authorization Dependencies (dependencies/authz.py)

```python
from functools import wraps

def require_permission(permission: Permission):
    """Dependency that checks if user has required permission."""
    async def check_permission(
        user: AuthenticatedUser = Depends(require_auth),
        settings: Settings = Depends(get_settings)
    ) -> AuthenticatedUser:
        if not settings.auth_enabled:
            return user

        user_permissions = set()
        for role in user.roles:
            user_permissions.update(ROLE_PERMISSIONS.get(role, set()))

        if permission not in user_permissions:
            raise HTTPException(403, f"Permission denied: {permission.value}")

        return user

    return check_permission

async def check_server_access(
    server_id: str,
    user: AuthenticatedUser,
    ironic_client: IronicClient,
    settings: Settings
) -> bool:
    """
    Check if user can access a specific server.

    Admins can access all servers.
    Others can only access servers they own or are leased to them.
    """
    if not settings.auth_enabled:
        return True

    if "admin" in user.roles:
        return True

    node = await ironic_client.get_node(server_id)

    # Check ownership (Ironic's owner field)
    if node.owner == user.id:
        return True

    # Check lease (Ironic's lessee field)
    if node.lessee == user.id:
        return True

    return False
```

### 3. Service Layer Updates

Services receive user context for authorization:

```python
# services/server.py
class ServerService:
    async def list_servers(
        self,
        user: AuthenticatedUser,
        # ... other params
    ) -> ServerListResponse:
        """List servers - filtered by ownership for non-admins."""
        nodes = await self.ironic.list_nodes()

        # Filter by ownership if not admin
        if "admin" not in user.roles:
            nodes = [n for n in nodes if n.owner == user.id or n.lessee == user.id]

        # ... rest of implementation
```

### 4. Router Updates

```python
# routers/server.py
@router.get("", response_model=ServerListResponse)
async def list_servers(
    user: AuthenticatedUser = Depends(require_permission(Permission.SERVER_LIST)),
    service: ServerService = Depends(get_server_service)
):
    """List servers visible to the current user."""
    return await service.list_servers(user=user, ...)

@router.post("/{server_id}/provision", response_model=ProvisionResponse)
async def provision_server(
    server_id: str,
    request: ProvisionRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.SERVER_PROVISION)),
    service: ProvisionService = Depends(get_provision_service),
    ironic: IronicClient = Depends(get_ironic_client),
    settings: Settings = Depends(get_settings)
):
    """Provision a server (must have access)."""
    if not await check_server_access(server_id, user, ironic, settings):
        raise HTTPException(403, f"Access denied to server {server_id}")

    return await service.provision_server(request)
```

### 5. Enrollment with Ownership

When enrolling servers, set the owner:

```python
# services/enroll.py
async def enroll_server(self, request: EnrollRequest, user: AuthenticatedUser) -> EnrollResponse:
    """Enroll server and set owner to enrolling user."""
    node = await self.ironic.create_node(
        name=request.name,
        driver=request.bmc.driver,
        driver_info=self._build_driver_info(request.bmc),
        owner=user.id,  # Set ownership
        # ...
    )
```

## Project Structure Additions

```
api/
├── dependencies/
│   └── authz.py
└── tests/
    └── test_authz.py
```

## Error Handling

| Error Condition | HTTP Status | Message |
|-----------------|-------------|---------|
| Missing required permission | 403 | "Permission denied: {permission}" |
| Not owner/lessee of server | 403 | "Access denied to server {id}" |

## Testing Requirements

1. Test role-based permission checks
2. Test ownership-based access control
3. Test admin bypass for all resources
4. Test lessee access
5. Test unauthorized access rejection

## Acceptance Criteria

- [ ] Role-based permissions enforced on all endpoints
- [ ] Resource-based access control using Ironic owner/lessee fields
- [ ] Admins can access all resources
- [ ] Users can only access owned/leased servers
- [ ] Enrollment sets owner to enrolling user
- [ ] Server lists filtered by ownership for non-admins
- [ ] All tests pass

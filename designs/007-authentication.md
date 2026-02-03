# Design 007: Authentication

**Status:** To Be Implemented

**Depends On:** Design 001

## Overview

This design adds stateless authentication to the API using JWT tokens or API keys. Authentication validates the identity of the caller without introducing local state.

## Architecture Principles

### Stateless Design

Authentication remains stateless:

- **No session storage**: JWT tokens are self-contained; validation doesn't require database lookups
- **No local user database**: User identity is validated against an external identity provider (IdP)
- **Token validation only**: The API validates tokens but doesn't issue them (IdP responsibility)
- **Horizontal scaling**: Any API instance can validate any token independently

## Goals

1. Add authentication middleware to all API endpoints
2. Support JWT bearer tokens (primary) and API keys (optional)
3. Extract user identity for downstream use (authorization, auditing)
4. Maintain backward compatibility with optional auth (configurable)

## Business Requirements

- Secure API access for production deployments
- Support integration with existing identity providers (Keycloak, Auth0, etc.)
- Allow service-to-service communication via API keys
- Configurable: auth can be disabled for development/testing

## Implementation Details

### 1. Configuration (config.py additions)

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Authentication settings
    auth_enabled: bool = False  # Disabled by default for backward compatibility
    jwt_secret: Optional[str] = None  # For symmetric validation (dev only)
    jwt_public_key_url: Optional[str] = None  # JWKS endpoint for IdP
    jwt_audience: Optional[str] = None  # Expected audience claim
    jwt_issuer: Optional[str] = None  # Expected issuer claim
    api_keys: list[str] = []  # Static API keys (for service accounts)
```

### 2. Auth Schema (schemas/auth.py)

```python
class AuthenticatedUser(BaseModel):
    """Represents an authenticated caller."""
    id: str  # Subject claim from JWT or API key identifier
    email: Optional[str] = None
    name: Optional[str] = None
    roles: list[str] = []  # For future authorization
    auth_method: Literal["jwt", "api_key"]
```

### 3. Auth Dependencies (dependencies/auth.py)

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    settings: Settings = Depends(get_settings)
) -> Optional[AuthenticatedUser]:
    """
    Validate authentication and return user identity.

    Returns None if auth is disabled.
    Raises 401 if auth is enabled but credentials are invalid.
    """
    if not settings.auth_enabled:
        return None

    if not credentials:
        raise HTTPException(401, "Authentication required")

    token = credentials.credentials

    # Try JWT validation first
    user = await _validate_jwt(token, settings)
    if user:
        return user

    # Try API key validation
    user = await _validate_api_key(token, settings)
    if user:
        return user

    raise HTTPException(401, "Invalid credentials")

async def require_auth(
    user: Optional[AuthenticatedUser] = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
) -> AuthenticatedUser:
    """Require authentication - raises 401 if not authenticated."""
    if settings.auth_enabled and not user:
        raise HTTPException(401, "Authentication required")
    # Return a default user for unauthenticated access when auth disabled
    return user or AuthenticatedUser(id="anonymous", auth_method="api_key")
```

### 4. JWT Validation

```python
import jwt
from jwt import PyJWKClient

async def _validate_jwt(token: str, settings: Settings) -> Optional[AuthenticatedUser]:
    """Validate JWT token and extract user identity."""
    try:
        # Get signing key from JWKS endpoint or use symmetric secret
        if settings.jwt_public_key_url:
            jwks_client = PyJWKClient(settings.jwt_public_key_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
        else:
            key = settings.jwt_secret

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256", "HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )

        return AuthenticatedUser(
            id=payload["sub"],
            email=payload.get("email"),
            name=payload.get("name"),
            roles=payload.get("roles", []),
            auth_method="jwt"
        )
    except jwt.InvalidTokenError:
        return None
```

### 5. Router Updates

Existing routers add the auth dependency:

```python
# Example: routers/server.py
@router.get("", response_model=ServerListResponse)
async def list_servers(
    user: AuthenticatedUser = Depends(require_auth),  # Add this
    service: ServerService = Depends(get_server_service)
):
    """List all servers with optional filtering."""
    # user is available for authorization/auditing
    return await service.list_servers(...)
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyJWT | ^2.8 | JWT token validation |

## Project Structure Additions

```
api/
├── schemas/
│   └── auth.py
├── dependencies/
│   ├── __init__.py
│   └── auth.py
└── tests/
    └── test_auth.py
```

## Error Handling

| Error Condition | HTTP Status | Message |
|-----------------|-------------|---------|
| Missing credentials (auth enabled) | 401 | "Authentication required" |
| Invalid/expired JWT | 401 | "Invalid credentials" |
| Invalid API key | 401 | "Invalid credentials" |

## Testing Requirements

1. Test auth disabled mode (backward compatibility)
2. Test valid JWT token validation
3. Test expired/invalid JWT rejection
4. Test API key validation
5. Test JWKS endpoint integration (mocked)

## Acceptance Criteria

- [ ] Auth can be enabled/disabled via configuration
- [ ] JWT tokens validated against configurable IdP
- [ ] API keys supported for service accounts
- [ ] All endpoints receive AuthenticatedUser when auth enabled
- [ ] 401 returned for invalid/missing credentials when auth enabled
- [ ] Existing functionality unchanged when auth disabled
- [ ] All tests pass

# Design 009: Audit Logging

**Status:** To Be Implemented

**Depends On:** Design 007

## Overview

This design adds structured audit logging to track all API operations. Logs are emitted to stdout in JSON format for consumption by external log aggregators, maintaining the stateless architecture.

## Architecture Principles

### Stateless Design

Audit logging remains stateless:

- **No local audit database**: Logs are emitted to stdout, not stored locally
- **External aggregation**: Log aggregators (ELK, Loki, CloudWatch, etc.) handle storage and search
- **Structured JSON format**: Machine-parseable logs enable filtering and alerting
- **Fire-and-forget**: Logging doesn't block or affect request processing

## Goals

1. Log all API operations with user identity and outcome
2. Use structured JSON format for machine parsing
3. Include sufficient context for security auditing
4. Zero performance impact on request handling
5. Support correlation IDs for request tracing

## Business Requirements

- Security team can audit who accessed what and when
- Operations can trace requests across services
- Compliance requirements for access logging
- Integration with existing log infrastructure

## Implementation Details

### 1. Configuration (config.py additions)

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Audit logging settings
    audit_logging_enabled: bool = True
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
```

### 2. Audit Log Schema

```python
# schemas/audit.py
class AuditLogEntry(BaseModel):
    """Structure of an audit log entry."""
    timestamp: datetime
    correlation_id: str

    # Request info
    method: str
    path: str
    query_params: Optional[dict]

    # User info (from auth)
    user_id: Optional[str]
    user_email: Optional[str]
    auth_method: Optional[str]

    # Response info
    status_code: int
    duration_ms: float

    # Resource info (when applicable)
    resource_type: Optional[str]  # "server", "provision", etc.
    resource_id: Optional[str]
    action: Optional[str]  # "list", "create", "provision", "unprovision"

    # Error info (when applicable)
    error_message: Optional[str]
```

### 3. Logging Configuration (logging_config.py)

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields from audit middleware
        if hasattr(record, "audit"):
            log_data["audit"] = record.audit

        return json.dumps(log_data)

def configure_logging(settings: Settings):
    """Configure application logging."""
    logger = logging.getLogger("ironic_aio")
    logger.setLevel(settings.log_level)

    handler = logging.StreamHandler()

    if settings.log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    logger.addHandler(handler)
    return logger
```

### 4. Audit Middleware (middleware/audit.py)

```python
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests."""

    def __init__(self, app, logger, settings):
        super().__init__(app)
        self.logger = logger
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.settings.audit_logging_enabled:
            return await call_next(request)

        # Generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        # Track timing
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build audit entry
        audit_entry = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params) or None,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }

        # Add user info if authenticated
        if hasattr(request.state, "user") and request.state.user:
            audit_entry["user_id"] = request.state.user.id
            audit_entry["user_email"] = request.state.user.email
            audit_entry["auth_method"] = request.state.user.auth_method

        # Add resource info if available
        if hasattr(request.state, "resource_type"):
            audit_entry["resource_type"] = request.state.resource_type
            audit_entry["resource_id"] = getattr(request.state, "resource_id", None)
            audit_entry["action"] = getattr(request.state, "action", None)

        # Log the entry
        self.logger.info(
            "api_request",
            extra={"audit": audit_entry}
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response
```

### 5. Resource Context Helpers

```python
# dependencies/audit.py
from fastapi import Request

def set_audit_context(
    request: Request,
    resource_type: str,
    action: str,
    resource_id: Optional[str] = None
):
    """Set audit context for the current request."""
    request.state.resource_type = resource_type
    request.state.action = action
    request.state.resource_id = resource_id
```

### 6. Router Integration

```python
# routers/server.py
@router.post("", response_model=EnrollResponse, status_code=201)
async def enroll_server(
    request: Request,
    enroll_request: EnrollRequest,
    user: AuthenticatedUser = Depends(require_auth),
    service: EnrollService = Depends(get_enroll_service)
):
    """Enroll a new server."""
    set_audit_context(request, "server", "enroll")
    result = await service.enroll_server(enroll_request, user)
    request.state.resource_id = result.server_id  # Update with created ID
    return result
```

### 7. App Integration (app.py additions)

```python
from middleware.audit import AuditMiddleware
from logging_config import configure_logging

# Configure logging
logger = configure_logging(settings)

# Add audit middleware
app.add_middleware(AuditMiddleware, logger=logger, settings=settings)
```

## Example Log Output

```json
{
  "timestamp": "2026-01-28T14:30:00.000Z",
  "level": "INFO",
  "logger": "ironic_aio",
  "message": "api_request",
  "audit": {
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "method": "POST",
    "path": "/servers",
    "query_params": null,
    "user_id": "user-123",
    "user_email": "admin@example.com",
    "auth_method": "jwt",
    "status_code": 201,
    "duration_ms": 245.32,
    "resource_type": "server",
    "resource_id": "node-uuid-456",
    "action": "enroll"
  }
}
```

## Project Structure Additions

```
api/
├── middleware/
│   ├── __init__.py
│   └── audit.py
├── dependencies/
│   └── audit.py
├── logging_config.py
└── tests/
    └── test_audit.py
```

## Testing Requirements

1. Test audit log format is valid JSON
2. Test correlation ID generation and propagation
3. Test user info included when authenticated
4. Test resource context captured correctly
5. Test audit can be disabled via config
6. Test log output to stdout (capture in tests)

## Acceptance Criteria

- [ ] All API requests logged with timestamp, method, path, status
- [ ] User identity included when authenticated
- [ ] Correlation IDs generated and returned in response headers
- [ ] Resource type and action captured for business operations
- [ ] JSON format suitable for log aggregators
- [ ] Audit logging can be disabled via configuration
- [ ] Performance impact negligible (<1ms overhead)
- [ ] All tests pass

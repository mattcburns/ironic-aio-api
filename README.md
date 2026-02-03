# Ironic AIO API

## Development Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the API

Start the unified server (REST + MCP):

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage (requires pytest-cov: `pip install pytest-cov`, enforcing 80% minimum)
pytest --cov=. --cov-report=term-missing --cov-fail-under=80

# Run specific test file
pytest tests/test_health_service.py

# Run tests matching a pattern
pytest -k "health"
```

## Dependency Justifications

| Package | Purpose |
| --- | --- |
| fastapi | REST API framework with automatic OpenAPI generation |
| uvicorn | ASGI server for running FastAPI |
| pydantic | Data validation and schema models |
| pydantic-settings | Environment-based configuration management |
| mcp | Model Context Protocol server implementation |
| httpx | Async HTTP client used by MCP and future Ironic calls |
| openstacksdk | Official OpenStack SDK used for Ironic client integration |
| pytest | Testing framework |
| pytest-asyncio | Async test support |

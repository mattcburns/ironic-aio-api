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

## Ironic Connection Settings

Configure Ironic authentication and TLS verification with environment variables:

- `IRONIC_AIO_IRONIC_BASIC_AUTH_USERNAME`: Optional Ironic basic auth username
- `IRONIC_AIO_IRONIC_BASIC_AUTH_PASSWORD`: Optional Ironic basic auth password
- `IRONIC_AIO_IRONIC_SKIP_CA_VERIFICATION`: Set to `true` to skip TLS CA verification

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

## Building Container Images

The project includes a Python-based build automation script (`build.py`) that handles containerizing the API. This script uses only Python built-in libraries and works identically both locally and in CI/CD environments.

### Prerequisites

- Docker must be installed and accessible in your PATH

### Local Container Builds

Build the container image with the default configuration:

```bash
python build.py build
```

Build and tag with a specific version:

```bash
python build.py build --tag v1.0.0
```

Build and push to a registry (Docker Hub):

```bash
python build.py build --tag latest --push
```

Build and push to GitHub Container Registry:

```bash
python build.py build --tag latest --push --registry ghcr.io --repo mattcburns/ironic-aio-api
```

### Build Script Options

The `build.py` script supports the following options:

- `--tag`: Docker image tag (default: `latest` or `DOCKER_TAG` environment variable)
- `--registry`: Container registry (default: `docker.io` or `DOCKER_REGISTRY` environment variable)
- `--repo`: Repository name (default: `mattcburns/ironic-aio-api` or `DOCKER_REPO` environment variable)
- `--push`: Push image to registry after successful build
- `--dockerfile`: Path to Dockerfile (default: `Dockerfile`)
- `--context`: Build context (default: `.`)

### Environment Variables

Configure builds using environment variables:

```bash
export DOCKER_REGISTRY=ghcr.io
export DOCKER_REPO=mattcburns/ironic-aio-api
export DOCKER_TAG=v1.0.0

python build.py build --push
```

### Build Metadata

After each successful build, the script saves build metadata to `build-metadata.json` containing:

- Image name and tag
- Registry information
- Image digest (SHA256 hash)
- Push status

### GitHub Actions Automation

The repository includes an automated GitHub Actions workflow (`.github/workflows/container-build.yml`) that:

- Builds the container image on pushes to `master` and pull requests
- Automatically creates and pushes versioned releases when Git tags (v*) are pushed
- Supports manual builds with custom tags and registries via `workflow_dispatch`
- Uses GitHub Container Registry (ghcr.io) by default for automated releases
- Uploads build metadata as artifacts for tracking

#### Workflow Triggers

The workflow runs automatically in these scenarios:

1. **Pull Requests**: Builds image to verify it can be created, no push
2. **Pushes to master**: Builds image, tags as `latest`
3. **Git Tags (v*)**: Builds and pushes versioned image (e.g., `v1.0.0`)
4. **Manual Dispatch**: Trigger manually with custom tag and registry

#### Release Process

To create a release:

1. Push a Git tag matching the pattern `v*`:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. The workflow automatically builds and pushes the image to `ghcr.io/${{ github.repository }}:v1.0.0`

3. The `latest` tag is updated when pushing to `master`

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

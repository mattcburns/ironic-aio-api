# Design 010: Build Automation and Container Release

**Status:** Implemented

**Depends On:** None

## Overview

This design establishes build automation infrastructure for containerizing the Ironic AIO API and enabling automated releases through GitHub Actions. The solution uses Python-based build scripts with only standard library dependencies, ensuring consistency between local development and CI/CD environments.

## Architecture

### Build Script (`build.py`)

The build script (`build.py`) provides a Python-based alternative to bash scripting for container operations:

**Key Components:**
- `BuildConfig`: Encapsulates build configuration (registry, repository, tag)
- `ContainerBuilder`: Handles Docker build and push operations
- Environment validation: Ensures Docker is installed and files exist
- Metadata generation: Saves build information to `build-metadata.json`

**Features:**
- Supports custom registries, repositories, and image tags
- Configuration via CLI arguments or environment variables
- Validation before executing Docker commands
- JSON metadata output for CI/CD integration

### GitHub Actions Workflow

The `.github/workflows/container-build.yml` workflow automates container operations:

**Triggers:**
1. Pull requests to `master` (builds only, no push)
2. Pushes to `master` (builds and tags as `latest`)
3. Git tags matching `v*` (builds and pushes versioned release)
4. Manual dispatch via `workflow_dispatch` (custom tag/registry)

**Actions:**
- Sets up Python and Docker environment
- Determines image tag based on Git context
- Builds container image using `build.py`
- Pushes to registry (GitHub Container Registry by default)
- Uploads build metadata as workflow artifacts

## Implementation Details

### Files Created

1. **`build.py`** (440 lines)
   - Main build automation script
   - Uses only Python standard library
   - AGPL v3 licensed
   - Comprehensive help and documentation

2. **`.github/workflows/container-build.yml`** (96 lines)
   - GitHub Actions workflow for CI/CD
   - Multi-trigger support
   - Flexible registry configuration

### Configuration

**Build Script Options:**
- `--tag`: Image tag (default: `latest` or `DOCKER_TAG` env var)
- `--registry`: Registry URL (default: `docker.io` or `DOCKER_REGISTRY` env var)
- `--repo`: Repository name (default: `mattcburns/ironic-aio-api` or `DOCKER_REPO` env var)
- `--push`: Push to registry after build
- `--dockerfile`: Path to Dockerfile (default: `Dockerfile`)
- `--context`: Build context directory (default: `.`)

**Environment Variables:**
- `DOCKER_REGISTRY`: Registry URL
- `DOCKER_REPO`: Repository name
- `DOCKER_TAG`: Image tag

### Release Workflow

**Creating a Release:**
```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow automatically:
1. Detects the version tag
2. Builds the container image
3. Pushes to `ghcr.io/mattcburns/ironic-aio-api:v1.0.0`

## Design Rationale

### Python-Only Implementation

Build script uses only Python standard library:
- **Consistency**: Same environment as application code
- **Portability**: Works on any system with Python and Docker
- **No external dependencies**: Reduces installation complexity
- **Alignment with project philosophy**: Minimal, well-proven solutions

### Standard Docker Registry Support

The design supports any Docker-compatible registry:
- Docker Hub (default)
- GitHub Container Registry (GHCR)
- Private registries
- AWS ECR, Azure ACR, etc.

### Metadata Export

Build metadata (`build-metadata.json`) provides:
- Image digest for reproducibility
- Registry information for tracking
- Push status for auditing

## Testing Considerations

The build script includes error handling for:
- Docker not installed or unavailable
- Missing Dockerfile
- Invalid build context
- Failed build or push operations

Manual testing should verify:
1. Local builds work with default settings
2. Custom tags/registries work correctly
3. Push operation succeeds with valid credentials
4. GitHub Actions workflow triggers correctly
5. Metadata file is generated after build

## Documentation

Complete documentation in [README.md](../README.md) includes:
- Prerequisites (Docker installation)
- Local build examples
- Build script options reference
- Environment variable configuration
- GitHub Actions workflow explanation
- Release process instructions

## Future Enhancements

Potential improvements (not in this design):
- Image signing and verification
- Multi-architecture builds (amd64, arm64)
- Dependency scanning and CVE reporting
- Container registry authentication
- Automated release notes generation

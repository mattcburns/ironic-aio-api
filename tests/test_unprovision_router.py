"""Tests for the unprovision REST router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas.server import ServerSummary
from schemas.unprovision import UnprovisionResponse, UnprovisionStatus


@pytest.fixture()
def mock_active_server():
    """Create a mock active server."""
    now = datetime.now(timezone.utc)
    return ServerSummary(
        id="test-server-uuid",
        name="test-server",
        provision_state="active",
        power_state="power on",
        resource_class="baremetal",
        is_available=False,
        properties={"cpus": 16, "memory_mb": 65536},
        created_at=now,
        updated_at=now
    )


@pytest.fixture()
def mock_server_service(mock_active_server):
    """Create a mock server service."""
    service = MagicMock()
    service.get_server = AsyncMock(return_value=mock_active_server)
    return service


@pytest.fixture()
def mock_unprovision_service():
    """Create a mock unprovision service."""
    service = MagicMock()
    now = datetime.now(timezone.utc)

    # Mock unprovision_server method
    service.unprovision_server = AsyncMock(
        return_value=UnprovisionResponse(
            server_id="test-server-uuid",
            server_name="test-server",
            status="accepted",
            message="Unprovisioning of test-server initiated",
            started_at=now
        )
    )

    # Mock get_unprovision_status method
    service.get_unprovision_status = AsyncMock(
        return_value=UnprovisionStatus(
            server_id="test-server-uuid",
            status="in_progress",
            provision_state="cleaning",
            progress_percent=50,
            message="Unprovisioning status: cleaning",
            started_at=now,
            completed_at=None
        )
    )

    return service


@pytest.mark.asyncio
async def test_unprovision_server_endpoint_success(client, mock_unprovision_service) -> None:
    """Test successful unprovisioning via REST endpoint."""
    from app import app
    from dependencies import get_unprovision_service

    request_data = {
        "server_id": "test-server-uuid",
        "clean": True
    }

    # Override the dependency
    app.dependency_overrides[get_unprovision_service] = lambda: mock_unprovision_service

    try:
        response = client.post("/unprovision", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert data["server_id"] == "test-server-uuid"
        assert data["status"] == "accepted"
        assert "message" in data
        assert "started_at" in data
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_unprovision_service, None)


@pytest.mark.asyncio
async def test_unprovision_server_endpoint_without_clean(client, mock_unprovision_service) -> None:
    """Test unprovisioning without cleaning via REST endpoint."""
    from app import app
    from dependencies import get_unprovision_service

    request_data = {
        "server_id": "test-server-uuid",
        "clean": False
    }

    # Override the dependency
    app.dependency_overrides[get_unprovision_service] = lambda: mock_unprovision_service

    try:
        response = client.post("/unprovision", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_unprovision_service, None)


@pytest.mark.asyncio
async def test_unprovision_server_endpoint_missing_server_id(client) -> None:
    """Test unprovisioning fails with missing server_id."""
    request_data = {
        "clean": True
        # Missing server_id
    }

    response = client.post("/unprovision", json=request_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_unprovision_server_endpoint_default_clean(client, mock_unprovision_service) -> None:
    """Test unprovisioning defaults to clean=True."""
    from app import app
    from dependencies import get_unprovision_service

    request_data = {
        "server_id": "test-server-uuid"
        # clean defaults to True
    }

    # Override the dependency
    app.dependency_overrides[get_unprovision_service] = lambda: mock_unprovision_service

    try:
        response = client.post("/unprovision", json=request_data)

        assert response.status_code == 202
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_unprovision_service, None)


@pytest.mark.asyncio
async def test_get_unprovision_status_endpoint(client, mock_unprovision_service) -> None:
    """Test getting unprovision status via REST endpoint."""
    from app import app
    from dependencies import get_unprovision_service

    # Override the dependency
    app.dependency_overrides[get_unprovision_service] = lambda: mock_unprovision_service

    try:
        response = client.get("/unprovision/test-server-uuid")

        assert response.status_code == 200
        data = response.json()
        assert data["server_id"] == "test-server-uuid"
        assert "status" in data
        assert "provision_state" in data
        assert "message" in data
        assert "started_at" in data
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_unprovision_service, None)


@pytest.mark.asyncio
async def test_get_unprovision_status_structure(client, mock_unprovision_service) -> None:
    """Test unprovision status response structure."""
    from app import app
    from dependencies import get_unprovision_service

    # Override the dependency
    app.dependency_overrides[get_unprovision_service] = lambda: mock_unprovision_service

    try:
        response = client.get("/unprovision/test-server-uuid")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        assert "server_id" in data
        assert "status" in data
        assert "provision_state" in data
        assert "message" in data
        assert "started_at" in data

        # Status should be one of the expected values
        assert data["status"] in ["in_progress", "completed", "failed"]
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_unprovision_service, None)

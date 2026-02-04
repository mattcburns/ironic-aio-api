"""Tests for the unprovision REST router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.server import ServerSummary


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


@pytest.mark.asyncio
async def test_unprovision_server_endpoint_success(client, mock_server_service) -> None:
    """Test successful unprovisioning via REST endpoint."""
    from unittest.mock import patch

    request_data = {
        "server_id": "test-server-uuid",
        "clean": True
    }

    with patch('dependencies.get_server_service', return_value=mock_server_service):
        response = client.post("/unprovision", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert data["server_id"] == "test-server-uuid"
    assert data["operation_id"] == "test-server-uuid"
    assert data["status"] == "accepted"
    assert "message" in data
    assert "started_at" in data


@pytest.mark.asyncio
async def test_unprovision_server_endpoint_without_clean(client, mock_server_service) -> None:
    """Test unprovisioning without cleaning via REST endpoint."""
    from unittest.mock import patch

    request_data = {
        "server_id": "test-server-uuid",
        "clean": False
    }

    with patch('dependencies.get_server_service', return_value=mock_server_service):
        response = client.post("/unprovision", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"


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
async def test_unprovision_server_endpoint_default_clean(client, mock_server_service) -> None:
    """Test unprovisioning defaults to clean=True."""
    from unittest.mock import patch

    request_data = {
        "server_id": "test-server-uuid"
        # clean defaults to True
    }

    with patch('dependencies.get_server_service', return_value=mock_server_service):
        response = client.post("/unprovision", json=request_data)

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_get_unprovision_status_endpoint(client) -> None:
    """Test getting unprovision status via REST endpoint."""
    response = client.get("/unprovision/test-server-uuid")

    assert response.status_code == 200
    data = response.json()
    assert data["operation_id"] == "test-server-uuid"
    assert data["server_id"] == "test-server-uuid"
    assert "status" in data
    assert "provision_state" in data
    assert "message" in data
    assert "started_at" in data


@pytest.mark.asyncio
async def test_get_unprovision_status_structure(client) -> None:
    """Test unprovision status response structure."""
    response = client.get("/unprovision/test-server-uuid")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields
    assert "operation_id" in data
    assert "server_id" in data
    assert "status" in data
    assert "provision_state" in data
    assert "message" in data
    assert "started_at" in data

    # Status should be one of the expected values
    assert data["status"] in ["in_progress", "completed", "failed"]

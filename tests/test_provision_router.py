"""Tests for the provision REST router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from schemas.server import ServerListResponse, ServerSummary


@pytest.fixture()
def mock_server_service():
    """Create a mock server service."""
    service = MagicMock()
    now = datetime.now(timezone.utc)
    server = ServerSummary(
        id="test-server-uuid",
        name="test-server",
        provision_state="available",
        power_state="power on",
        resource_class="baremetal",
        is_available=True,
        properties={"cpus": 16, "memory_mb": 65536},
        created_at=now,
        updated_at=now
    )
    response = ServerListResponse(
        servers=[server],
        total=1,
        page=1,
        page_size=50
    )
    service.list_servers = AsyncMock(return_value=response)
    return service


@pytest.mark.asyncio
async def test_provision_server_endpoint_success(client, mock_server_service) -> None:
    """Test successful provisioning via REST endpoint."""
    request_data = {
        "server_id": "test-server-uuid",
        "image_source": "https://example.com/ubuntu-22.04.qcow2",
        "image_checksum": "abc123def456",
    }

    with patch('dependencies.get_server_service', return_value=mock_server_service):
        response = client.post("/provision", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert data["server_id"] == "test-server-uuid"
    assert data["operation_id"] == "test-server-uuid"
    assert data["status"] == "accepted"
    assert "message" in data
    assert "started_at" in data


@pytest.mark.asyncio
async def test_provision_server_endpoint_auto_select(client, mock_server_service) -> None:
    """Test provisioning with auto-selection."""
    request_data = {
        "image_source": "https://example.com/ubuntu-22.04.qcow2",
    }

    with patch('dependencies.get_server_service', return_value=mock_server_service):
        response = client.post("/provision", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert "operation_id" in data
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_provision_server_endpoint_with_resource_class(client, mock_server_service) -> None:
    """Test provisioning with resource class filter."""
    request_data = {
        "image_source": "https://example.com/ubuntu-22.04.qcow2",
        "resource_class": "baremetal",
    }

    with patch('dependencies.get_server_service', return_value=mock_server_service):
        response = client.post("/provision", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_provision_server_endpoint_with_config_drive(client, mock_server_service) -> None:
    """Test provisioning with cloud-init config drive."""
    request_data = {
        "server_id": "test-server-uuid",
        "image_source": "https://example.com/ubuntu-22.04.qcow2",
        "config_drive": {
            "hostname": "test-host",
            "network": {
                "version": 2,
                "ethernets": {
                    "eth0": {
                        "dhcp4": True
                    }
                }
            }
        }
    }

    with patch('dependencies.get_server_service', return_value=mock_server_service):
        response = client.post("/provision", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_provision_server_endpoint_missing_image(client) -> None:
    """Test provisioning fails with missing image."""
    request_data = {
        "server_id": "test-server-uuid",
        # Missing image_source
    }

    response = client.post("/provision", json=request_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_provision_status_endpoint(client) -> None:
    """Test getting provision status via REST endpoint."""
    response = client.get("/provision/test-server-uuid")

    assert response.status_code == 200
    data = response.json()
    assert data["operation_id"] == "test-server-uuid"
    assert data["server_id"] == "test-server-uuid"
    assert "status" in data
    assert "provision_state" in data
    assert "message" in data
    assert "started_at" in data


@pytest.mark.asyncio
async def test_get_provision_status_structure(client) -> None:
    """Test provision status response structure."""
    response = client.get("/provision/test-server-uuid")

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

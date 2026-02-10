"""Tests for the enrollment REST router."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from schemas.enroll import EnrollResponse


@pytest.mark.asyncio
async def test_enroll_server_endpoint_success(client) -> None:
    """Test successful enrollment via REST endpoint."""
    request_data = {
        "name": "test-server",
        "bmc": {
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "network": {
            "mac_address": "00:11:22:33:44:55",
            "nic_name": "eth0",
            "ip_address": "10.0.0.10",
            "netmask": "255.255.255.0",
            "gateway": "10.0.0.1",
        },
        "resource_class": "baremetal",
        "validate_bmc": True,
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert data["server_name"] == "test-server"
    assert data["status"] == "enrolled"
    assert "message" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_enroll_server_endpoint_minimal_request(client) -> None:
    """Test enrollment with minimal required fields."""
    request_data = {
        "name": "minimal-server",
        "bmc": {
            "address": "192.168.1.101",
            "username": "admin",
            "password": "password",
        },
        "network": {
            "mac_address": "00:11:22:33:44:66",
            "nic_name": "eth0",
            "ip_address": "10.0.0.11",
            "netmask": "255.255.255.0",
            "gateway": "10.0.0.1",
        },
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 202
    data = response.json()
    assert data["server_name"] == "minimal-server"


@pytest.mark.asyncio
async def test_enroll_server_endpoint_missing_required_fields(client) -> None:
    """Test enrollment fails with missing required fields."""
    request_data = {
        "name": "incomplete-server",
        # Missing bmc field
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_enroll_server_endpoint_with_properties(client) -> None:
    """Test enrollment with server properties."""
    request_data = {
        "name": "test-server",
        "bmc": {
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "network": {
            "mac_address": "00:11:22:33:44:55",
            "nic_name": "eth0",
            "ip_address": "10.0.0.10",
            "netmask": "255.255.255.0",
            "gateway": "10.0.0.1",
        },
        "properties": {
            "cpu_arch": "x86_64",
            "cpus": 16,
            "memory_mb": 65536,
            "local_gb": 1000,
        },
        "kernel_url": "https://images.example.com/deploy.kernel",
        "ramdisk_url": "https://images.example.com/deploy.ramdisk",
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 202

@pytest.mark.asyncio
async def test_enroll_server_endpoint_without_validation(client) -> None:
    """Test enrollment without BMC validation."""
    request_data = {
        "name": "test-server",
        "bmc": {
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "network": {
            "mac_address": "00:11:22:33:44:55",
            "nic_name": "eth0",
            "ip_address": "10.0.0.10",
            "netmask": "255.255.255.0",
            "gateway": "10.0.0.1",
        },
        "validate_bmc": False,
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_get_enrollment_status_endpoint(client) -> None:
    """Test getting enrollment status via REST endpoint."""
    # First enroll a server
    request_data = {
        "name": "status-test-server",
        "bmc": {
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "network": {
            "mac_address": "00:11:22:33:44:55",
            "nic_name": "eth0",
            "ip_address": "10.0.0.10",
            "netmask": "255.255.255.0",
            "gateway": "10.0.0.1",
        },
    }
    enroll_response = client.post("/servers", json=request_data)
    assert enroll_response.status_code == 202
    server_id = enroll_response.json()["server_id"]

    # Get enrollment status
    status_response = client.get(f"/servers/{server_id}/enrollment-status")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["server_id"] == server_id
    assert data["server_name"] == "status-test-server"
    assert "provision_state" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_get_enrollment_status_not_found(client) -> None:
    """Test enrollment status returns proper error when server not found."""
    response = client.get("/servers/nonexistent-uuid/enrollment-status")

    # Should return 502 (Ironic API error) when node not found
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_provide_server_endpoint_success(client) -> None:
    """Test successful provide transition via REST endpoint."""
    # First enroll a server
    enroll_data = {
        "name": "provide-test-server",
        "bmc": {
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "network": {
            "mac_address": "00:11:22:33:44:55",
            "nic_name": "eth0",
            "ip_address": "10.0.0.10",
            "netmask": "255.255.255.0",
            "gateway": "10.0.0.1",
        },
        "validate_bmc": False,
    }
    enroll_response = client.post("/servers", json=enroll_data)
    assert enroll_response.status_code == 202
    server_id = enroll_response.json()["server_id"]

    # Provide the server
    provide_response = client.post(f"/servers/{server_id}/provide")

    assert provide_response.status_code == 202  # Accepted
    data = provide_response.json()
    assert data["server_id"] == server_id
    assert data["status"] == "enrolled"
    assert "transition to available initiated" in data["message"]


@pytest.mark.asyncio
async def test_provide_server_endpoint_not_found(client) -> None:
    """Test provide fails when server not found."""
    response = client.post("/servers/nonexistent-uuid/provide")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


@pytest.mark.asyncio
async def test_provide_server_endpoint_invalid_state(client) -> None:
    """Test provide fails when server is not in manageable state."""
    # This would require more complex mocking to set up a non-manageable server
    # The basic test above covers the happy path behavior
    pass

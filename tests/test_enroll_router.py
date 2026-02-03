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
            "driver": "redfish",
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "resource_class": "baremetal",
        "validate_bmc": True,
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 201
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
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 201
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
            "driver": "redfish",
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "properties": {
            "cpu_arch": "x86_64",
            "cpus": 16,
            "memory_mb": 65536,
            "local_gb": 1000,
        },
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_enroll_server_endpoint_without_validation(client) -> None:
    """Test enrollment without BMC validation."""
    request_data = {
        "name": "test-server",
        "bmc": {
            "driver": "redfish",
            "address": "192.168.1.100",
            "username": "admin",
            "password": "password",
        },
        "validate_bmc": False,
    }

    response = client.post("/servers", json=request_data)

    assert response.status_code == 201

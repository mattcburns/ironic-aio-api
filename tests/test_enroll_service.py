"""Tests for the enrollment service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from schemas.enroll import BMCCredentials, EnrollRequest
from services.enroll import EnrollService


class FakeIronicClientForEnroll:
    """Test double for the Ironic client."""

    def __init__(self, existing_nodes: list[str] | None = None):
        """Initialize fake client.

        Args:
            existing_nodes: List of existing node names
        """
        self.existing_nodes = existing_nodes or []
        self.created_nodes = []


@pytest.fixture()
def fake_ironic_client_empty() -> FakeIronicClientForEnroll:
    """Create a fake Ironic client with no existing nodes."""
    return FakeIronicClientForEnroll()


@pytest.fixture()
def fake_ironic_client_with_nodes() -> FakeIronicClientForEnroll:
    """Create a fake Ironic client with existing nodes."""
    return FakeIronicClientForEnroll(existing_nodes=["existing-server"])


@pytest.mark.asyncio
async def test_enroll_server_success(
    fake_ironic_client_empty: FakeIronicClientForEnroll,
) -> None:
    """Test successful server enrollment."""
    service = EnrollService(ironic_client=fake_ironic_client_empty)

    request = EnrollRequest(
        name="test-server",
        bmc=BMCCredentials(
            driver="redfish",
            address="192.168.1.100",
            username="admin",
            password="password",
        ),
        resource_class="baremetal",
        validate_bmc=True,
    )

    result = await service.enroll_server(request)

    assert result.server_name == "test-server"
    assert result.status == "enrolled"
    assert result.provision_state == "enroll"
    assert "successfully enrolled" in result.message
    assert isinstance(result.created_at, datetime)
    assert result.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_enroll_server_without_bmc_validation(
    fake_ironic_client_empty: FakeIronicClientForEnroll,
) -> None:
    """Test enrollment without BMC validation."""
    service = EnrollService(ironic_client=fake_ironic_client_empty)

    request = EnrollRequest(
        name="test-server",
        bmc=BMCCredentials(
            driver="redfish",
            address="192.168.1.100",
            username="admin",
            password="password",
        ),
        validate_bmc=False,
    )

    result = await service.enroll_server(request)

    assert result.status == "enrolled"


@pytest.mark.asyncio
async def test_build_redfish_driver_info() -> None:
    """Test Redfish driver info building."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    bmc = BMCCredentials(
        driver="redfish",
        address="192.168.1.100",
        username="admin",
        password="password",
    )

    driver_info = service._build_redfish_driver_info(bmc)

    assert driver_info["redfish_address"] == "https://192.168.1.100"
    assert driver_info["redfish_username"] == "admin"
    assert driver_info["redfish_password"] == "password"
    assert driver_info["redfish_system_id"] == "/redfish/v1/Systems/1"


@pytest.mark.asyncio
async def test_build_driver_info_with_supported_driver() -> None:
    """Test driver info building with supported driver."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    bmc = BMCCredentials(
        driver="redfish",
        address="192.168.1.100",
        username="admin",
        password="password",
    )

    driver_info = service._build_driver_info(bmc)

    assert "redfish_address" in driver_info


@pytest.mark.asyncio
async def test_validate_name_unique_passes() -> None:
    """Test name uniqueness validation passes."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    # Should not raise
    await service._validate_name_unique("new-server")


@pytest.mark.asyncio
async def test_validate_bmc_connectivity_success() -> None:
    """Test BMC connectivity validation succeeds."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    result = await service._validate_bmc_connectivity("test-uuid")

    assert result is True

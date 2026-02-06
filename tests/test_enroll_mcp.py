"""Tests for the enrollment MCP tool."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from mcp_tools.enroll import enroll_server
from services.enroll import EnrollService
from tests.test_enroll_service import FakeIronicClientForEnroll


@pytest.fixture(autouse=True)
def _mock_enroll_service(monkeypatch):
    """Automatically mock the enrollment service for all MCP tests."""
    fake_ironic_client = FakeIronicClientForEnroll()
    service = EnrollService(ironic_client=fake_ironic_client)

    # Patch the dependencies module directly
    def mock_get_enroll_service():
        return service

    # Patch in both locations that might be imported
    monkeypatch.setattr("dependencies.get_enroll_service", mock_get_enroll_service)
    monkeypatch.setattr("mcp_tools.enroll.get_enroll_service", mock_get_enroll_service)


@pytest.mark.asyncio
async def test_enroll_server_mcp_tool_success() -> None:
    """Test successful enrollment via MCP tool."""
    result = await enroll_server(
        name="test-server",
        bmc_address="192.168.1.100",
        bmc_username="admin",
        bmc_password="password",
        mac_address="00:11:22:33:44:55",
        nic_name="eth0",
        ip_address="10.0.0.10",
        netmask="255.255.255.0",
        gateway="10.0.0.1",
        resource_class="baremetal",
    )

    assert result["server_name"] == "test-server"
    assert result["status"] == "enrolled"
    assert "message" in result
    assert "created_at" in result


@pytest.mark.asyncio
async def test_enroll_server_mcp_tool_minimal_params() -> None:
    """Test enrollment with minimal parameters."""
    result = await enroll_server(
        name="minimal-server",
        bmc_address="192.168.1.101",
        bmc_username="admin",
        bmc_password="password",
        mac_address="00:11:22:33:44:66",
        nic_name="eth0",
        ip_address="10.0.0.11",
        netmask="255.255.255.0",
        gateway="10.0.0.1",
    )

    assert result["server_name"] == "minimal-server"
    assert result["status"] == "enrolled"


@pytest.mark.asyncio
async def test_enroll_server_mcp_tool_redfish_driver() -> None:
    """Test enrollment with Redfish driver."""
    result = await enroll_server(
        name="redfish-server",
        bmc_address="192.168.1.102",
        bmc_username="admin",
        bmc_password="password",
        mac_address="00:11:22:33:44:77",
        nic_name="eth0",
        ip_address="10.0.0.12",
        netmask="255.255.255.0",
        gateway="10.0.0.1",
    )

    assert result["server_name"] == "redfish-server"
    assert result["status"] == "enrolled"


@pytest.mark.asyncio
async def test_enroll_server_mcp_tool_with_resource_class() -> None:
    """Test enrollment with resource class."""
    result = await enroll_server(
        name="classified-server",
        bmc_address="192.168.1.103",
        bmc_username="admin",
        bmc_password="password",
        mac_address="00:11:22:33:44:88",
        nic_name="eth0",
        ip_address="10.0.0.13",
        netmask="255.255.255.0",
        gateway="10.0.0.1",
        resource_class="compute",
    )

    assert result["server_name"] == "classified-server"
    assert result["status"] == "enrolled"




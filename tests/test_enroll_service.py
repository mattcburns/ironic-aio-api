"""Tests for the enrollment service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from schemas.enroll import BMCCredentials, EnrollRequest, NetworkInterface
from services.enroll import EnrollService


class FakeNode:
    """Fake Ironic node for testing."""

    def __init__(self, name: str, node_id: str | None = None):
        """Initialize fake node.

        Args:
            name: Node name
            node_id: Optional node UUID
        """
        self.name = name
        self.id = node_id or str(uuid4())
        self.driver = "redfish"
        self.driver_info = {}
        self.resource_class = None
        self.properties = {}
        self.ports = []


class FakeIronicClientForEnroll:
    """Test double for the Ironic client."""

    def __init__(self, existing_nodes: list[str] | None = None):
        """Initialize fake client.

        Args:
            existing_nodes: List of existing node names
        """
        self.existing_nodes = existing_nodes or []
        self.created_nodes = []
        self._nodes_by_name = {name: FakeNode(name) for name in self.existing_nodes}

    async def get_node_by_name(self, name: str) -> FakeNode | None:
        """Get a node by name.

        Args:
            name: Name of the node to retrieve

        Returns:
            Node if found, None otherwise
        """
        return self._nodes_by_name.get(name)

    async def create_node(
        self,
        name: str,
        driver: str,
        driver_info: dict,
        resource_class: str | None = None,
        properties: dict | None = None,
    ) -> FakeNode:
        """Create a new node.

        Args:
            name: Unique name for the node
            driver: Driver to use (e.g., 'redfish')
            driver_info: Driver-specific configuration
            resource_class: Resource class for the node
            properties: Node properties

        Returns:
            Created FakeNode object
        """
        node = FakeNode(name)
        node.driver = driver
        node.driver_info = driver_info
        node.resource_class = resource_class
        node.properties = properties or {}
        self.created_nodes.append(node)
        self._nodes_by_name[name] = node
        return node

    async def add_node_port(
        self,
        node_id: str,
        mac_address: str,
        extra: dict | None = None,
    ) -> object:
        """Add a network port to a node.

        Args:
            node_id: UUID of the node
            mac_address: MAC address of the port
            extra: Additional port configuration

        Returns:
            Created port object (dict for testing)
        """
        port = {
            "mac_address": mac_address,
            "extra": extra or {},
        }
        # Store port in the node (for testing purposes)
        for node in self.created_nodes:
            if node.id == node_id:
                node.ports.append(port)
                break
        return port

    async def validate_node(self, node_id: str) -> dict:
        """Validate node driver (test BMC connectivity).

        Args:
            node_id: UUID of the node to validate

        Returns:
            Validation result dictionary
        """
        return {"result": "success"}



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
            address="192.168.1.100",
            username="admin",
            password="password",
        ),
        network=NetworkInterface(
            mac_address="00:11:22:33:44:55",
            nic_name="eth0",
            ip_address="10.0.0.10",
            netmask="255.255.255.0",
            gateway="10.0.0.1",
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
            address="192.168.1.100",
            username="admin",
            password="password",
        ),
        network=NetworkInterface(
            mac_address="00:11:22:33:44:55",
            nic_name="eth0",
            ip_address="10.0.0.10",
            netmask="255.255.255.0",
            gateway="10.0.0.1",
        ),
        validate_bmc=False,
    )

    result = await service.enroll_server(request)

    assert result.status == "enrolled"


@pytest.mark.asyncio
async def test_enroll_server_with_custom_redfish_system_id(
    fake_ironic_client_empty: FakeIronicClientForEnroll,
) -> None:
    """Test enrollment with custom Redfish system ID."""
    service = EnrollService(ironic_client=fake_ironic_client_empty)

    custom_system_id = "/redfish/v1/Systems/custom-123"
    request = EnrollRequest(
        name="test-server-custom",
        bmc=BMCCredentials(
            address="192.168.1.100",
            username="admin",
            password="password",
        ),
        network=NetworkInterface(
            mac_address="00:11:22:33:44:55",
            nic_name="eth0",
            ip_address="10.0.0.10",
            netmask="255.255.255.0",
            gateway="10.0.0.1",
        ),
        redfish_system_id=custom_system_id,
        validate_bmc=False,
    )

    result = await service.enroll_server(request)

    assert result.status == "enrolled"
    assert result.server_name == "test-server-custom"


@pytest.mark.asyncio
async def test_build_redfish_driver_info() -> None:
    """Test Redfish driver info building with default system ID."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    bmc = BMCCredentials(
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
async def test_build_redfish_driver_info_with_custom_system_id() -> None:
    """Test Redfish driver info building with custom system ID."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    bmc = BMCCredentials(
        address="192.168.1.100",
        username="admin",
        password="password",
    )

    custom_system_id = "/redfish/v1/Systems/custom-id"
    driver_info = service._build_redfish_driver_info(bmc, custom_system_id)

    assert driver_info["redfish_address"] == "https://192.168.1.100"
    assert driver_info["redfish_username"] == "admin"
    assert driver_info["redfish_password"] == "password"
    assert driver_info["redfish_system_id"] == custom_system_id


@pytest.mark.asyncio
async def test_build_driver_info_with_supported_driver() -> None:
    """Test driver info building with supported driver."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    bmc = BMCCredentials(
        address="192.168.1.100",
        username="admin",
        password="password",
    )

    driver_info = service._build_redfish_driver_info(bmc)

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

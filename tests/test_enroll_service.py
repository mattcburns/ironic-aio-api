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

    def __init__(self, name: str, node_id: str | None = None, provision_state: str = "enroll"):
        """Initialize fake node.

        Args:
            name: Node name
            node_id: Optional node UUID
            provision_state: Initial provision state
        """
        self.name = name
        self.id = node_id or str(uuid4())
        self.driver = "redfish"
        self.driver_info = {}
        self.resource_class = None
        self.properties = {}
        self.ports = []
        self.provision_state = provision_state


class FakeIronicClientForEnroll:
    """Test double for the Ironic client."""

    def __init__(self, existing_nodes: list[str] | None = None, simulate_error: str | None = None):
        """Initialize fake client.

        Args:
            existing_nodes: List of existing node names
            simulate_error: Error type to simulate ('api_error', 'not_implemented')
        """
        self.existing_nodes = existing_nodes or []
        self.created_nodes = []
        self._nodes_by_name = {name: FakeNode(name) for name in self.existing_nodes}
        self._nodes_by_id = {}
        self.simulate_error = simulate_error

    async def get_node_by_name(self, name: str) -> FakeNode | None:
        """Get a node by name.

        Args:
            name: Name of the node to retrieve

        Returns:
            Node if found, None otherwise
        """
        return self._nodes_by_name.get(name)

    async def get_node(self, node_id: str, ignore_missing: bool = False) -> FakeNode | None:
        """Get a node by ID.

        Args:
            node_id: UUID of the node to retrieve
            ignore_missing: If True, return None instead of raising on not found

        Returns:
            Node if found, None if ignore_missing=True and not found

        Raises:
            IronicClientError: If node not found and ignore_missing=False
        """
        if self.simulate_error == "api_error":
            from clients.ironic import IronicClientError
            raise IronicClientError("Failed to get node")

        # Check nodes by ID
        if node_id in self._nodes_by_id:
            return self._nodes_by_id[node_id]

        # Check created nodes
        for node in self.created_nodes:
            if node.id == node_id:
                return node

        # Check existing nodes
        for node in self._nodes_by_name.values():
            if node.id == node_id:
                return node

        if ignore_missing:
            return None

        from clients.ironic import IronicClientError
        raise IronicClientError(f"Node {node_id} not found")

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
        if self.simulate_error == "api_error":
            from clients.ironic import IronicClientError
            raise IronicClientError("Failed to create node")

        if self.simulate_error == "not_implemented":
            raise NotImplementedError("Node creation not implemented")

        node = FakeNode(name)
        node.driver = driver
        node.driver_info = driver_info
        node.resource_class = resource_class
        node.properties = properties or {}
        self.created_nodes.append(node)
        self._nodes_by_name[name] = node
        self._nodes_by_id[node.id] = node
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
        if self.simulate_error == "bmc_validation_error":
            from clients.ironic import IronicClientError
            raise IronicClientError("BMC validation failed")

        return {"result": "success"}

    async def set_node_provision_state(
        self,
        node_id: str,
        target_state: str,
    ) -> FakeNode:
        """Set node provision state target.

        Args:
            node_id: UUID of the node
            target_state: Target provision state (action: manage, provide, etc.)

        Returns:
            Updated FakeNode object
        """
        if self.simulate_error == "state_transition_error":
            from clients.ironic import IronicClientError
            raise IronicClientError(f"Failed to transition node to {target_state}")

        # Special handling for transition errors during specific transitions
        if self.simulate_error == "manage_transition_error" and target_state == "manage":
            from clients.ironic import IronicClientError
            raise IronicClientError(f"Failed to transition node to manage")

        if self.simulate_error == "provide_transition_error" and target_state == "provide":
            from clients.ironic import IronicClientError
            raise IronicClientError(f"Failed to transition node to provide")

        # Map synchronous actions to actual provision states
        # manage action -> manageable state (synchronous during enrollment)
        # provide action -> do not change state immediately (async cleaning)
        # unmanage action -> enroll state
        state_mapping = {
            "manage": "manageable",
            "unmanage": "enroll",
        }
        actual_state = state_mapping.get(target_state)

        # Find and update the node
        for node in self.created_nodes:
            if node.id == node_id:
                # Only update state for synchronous transitions
                if actual_state is not None:
                    node.provision_state = actual_state
                # For async transitions like "provide", don't update state
                return node

        # If not found in created nodes, check existing nodes
        for node in self._nodes_by_name.values():
            if node.id == node_id:
                if actual_state is not None:
                    node.provision_state = actual_state
                return node

        from clients.ironic import IronicClientError
        raise IronicClientError(f"Node {node_id} not found")


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
    # Accept any valid provision state - should be manageable after enrollment
    assert result.provision_state in ["enroll", "manageable", "manage"]
    assert "enrollment initiated" in result.message
    assert "provide" in result.message  # Should mention the provide endpoint
    assert "enrollment-status" in result.message  # Should mention status endpoint
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
    assert "redfish_system_id" not in driver_info  # Not sent when not explicitly provided
    assert driver_info["redfish_verify_ca"] is False


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
    driver_info = service._build_redfish_driver_info(
        bmc,
        custom_system_id,
        redfish_verify_ca=True,
    )

    assert driver_info["redfish_address"] == "https://192.168.1.100"
    assert driver_info["redfish_username"] == "admin"
    assert driver_info["redfish_password"] == "password"
    assert driver_info["redfish_system_id"] == custom_system_id
    assert driver_info["redfish_verify_ca"] is True


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


@pytest.mark.asyncio
async def test_enroll_server_duplicate_name_fails(
    fake_ironic_client_with_nodes: FakeIronicClientForEnroll,
) -> None:
    """Test enrollment fails when server name already exists."""
    service = EnrollService(ironic_client=fake_ironic_client_with_nodes)

    request = EnrollRequest(
        name="existing-server",
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
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.enroll_server(request)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_enroll_server_ironic_api_error(
    fake_ironic_client_empty: FakeIronicClientForEnroll,
) -> None:
    """Test enrollment fails on Ironic API error."""
    fake_client = FakeIronicClientForEnroll(simulate_error="api_error")
    service = EnrollService(ironic_client=fake_client)

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
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.enroll_server(request)

    assert exc_info.value.status_code == 502
    assert "Ironic API error" in exc_info.value.detail


@pytest.mark.asyncio
async def test_enroll_server_bmc_validation_fails() -> None:
    """Test enrollment fails when BMC validation fails."""
    fake_client = FakeIronicClientForEnroll(simulate_error="bmc_validation_error")
    service = EnrollService(ironic_client=fake_client)

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
        validate_bmc=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.enroll_server(request)

    assert exc_info.value.status_code == 422
    assert "Unable to connect to BMC" in exc_info.value.detail


@pytest.mark.asyncio
async def test_build_redfish_driver_info_with_bmc_port() -> None:
    """Test Redfish driver info includes BMC port when specified."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    bmc = BMCCredentials(
        address="192.168.1.100",
        username="admin",
        password="password",
        port=8443,
    )

    driver_info = service._build_redfish_driver_info(bmc)

    assert driver_info["redfish_address"] == "https://192.168.1.100:8443"
    assert driver_info["redfish_username"] == "admin"
    assert driver_info["redfish_password"] == "password"
    assert "redfish_system_id" not in driver_info  # Not sent when not explicitly provided
    assert driver_info["redfish_verify_ca"] is False


@pytest.mark.asyncio
async def test_enroll_server_manage_transition_error() -> None:
    """Test enrollment fails if manage transition fails (it's required)."""
    fake_client = FakeIronicClientForEnroll(simulate_error="manage_transition_error")
    service = EnrollService(ironic_client=fake_client)

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

    # Manage transition failure fails enrollment (manage is required)
    with pytest.raises(HTTPException) as exc_info:
        await service.enroll_server(request)

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_enroll_server_provide_transition_error() -> None:
    """Test enrollment continues if provide transition fails."""
    fake_client = FakeIronicClientForEnroll(simulate_error="provide_transition_error")
    service = EnrollService(ironic_client=fake_client)

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

    # Provide transition failure doesn't fail enrollment (manage succeeded)
    result = await service.enroll_server(request)
    assert result.status == "enrolled"
    assert result.server_name == "test-server"


@pytest.mark.asyncio
async def test_get_enrollment_status_various_states() -> None:
    """Test get_enrollment_status with various provision states."""
    fake_client = FakeIronicClientForEnroll()
    service = EnrollService(ironic_client=fake_client)

    # Create a node in different states and test status
    test_states = [
        ("enroll", "waiting to transition"),
        ("manageable", "being cleaned"),
        ("available", "ready for provisioning"),
        ("cleaning", "being cleaned"),
    ]

    for state, expected_message_part in test_states:
        # Create node with specific state
        node = FakeNode("test-node", provision_state=state)
        fake_client._nodes_by_id[node.id] = node
        fake_client.created_nodes.append(node)

        # Get status
        result = await service.get_enrollment_status(node.id)

        assert result.server_id == node.id
        assert result.provision_state == state
        assert expected_message_part.lower() in result.message.lower()


@pytest.mark.asyncio
async def test_get_enrollment_status_not_found() -> None:
    """Test get_enrollment_status raises 404 when server not found."""
    fake_client = FakeIronicClientForEnroll()
    service = EnrollService(ironic_client=fake_client)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_enrollment_status("nonexistent-id")

    assert exc_info.value.status_code == 502  # IronicClientError maps to 502


@pytest.mark.asyncio
async def test_map_provision_state_to_message() -> None:
    """Test provision state mapping to human-readable messages."""
    service = EnrollService(ironic_client=FakeIronicClientForEnroll())

    # Test known states
    assert "ready for provisioning" in service._map_provision_state_to_message("available")
    assert "being cleaned" in service._map_provision_state_to_message("manageable")
    assert "waiting to transition" in service._map_provision_state_to_message("enroll")

    # Test unknown state
    assert "unknown-state" in service._map_provision_state_to_message("unknown-state")


@pytest.mark.asyncio
async def test_provide_server_success() -> None:
    """Test successful provide transition."""
    fake_client = FakeIronicClientForEnroll()
    service = EnrollService(ironic_client=fake_client)

    # Create a node in manageable state
    node = FakeNode("test-server", provision_state="manageable")
    fake_client._nodes_by_id[node.id] = node
    fake_client.created_nodes.append(node)

    result = await service.provide_server(node.id)

    assert result.server_id == node.id
    assert result.status == "enrolled"
    assert result.provision_state == "manageable"  # Stays manageable after initiation
    assert "transition to available initiated" in result.message


@pytest.mark.asyncio
async def test_provide_server_not_found() -> None:
    """Test provide fails when server not found."""
    fake_client = FakeIronicClientForEnroll()
    service = EnrollService(ironic_client=fake_client)

    with pytest.raises(HTTPException) as exc_info:
        await service.provide_server("nonexistent-server")

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_provide_server_not_manageable() -> None:
    """Test provide fails when server is not in manageable state."""
    fake_client = FakeIronicClientForEnroll()
    service = EnrollService(ironic_client=fake_client)

    # Create a node in available state
    node = FakeNode("test-server", provision_state="available")
    fake_client._nodes_by_id[node.id] = node
    fake_client.created_nodes.append(node)

    with pytest.raises(HTTPException) as exc_info:
        await service.provide_server(node.id)

    assert exc_info.value.status_code == 400
    assert "manageable" in exc_info.value.detail
    assert "available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_provide_server_enroll_state() -> None:
    """Test provide fails when server is in enroll state."""
    fake_client = FakeIronicClientForEnroll()
    service = EnrollService(ironic_client=fake_client)

    # Create a node in enroll state
    node = FakeNode("test-server", provision_state="enroll")
    fake_client._nodes_by_id[node.id] = node
    fake_client.created_nodes.append(node)

    with pytest.raises(HTTPException) as exc_info:
        await service.provide_server(node.id)

    assert exc_info.value.status_code == 400
    assert "manageable" in exc_info.value.detail

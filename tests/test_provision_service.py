"""Tests for the provision service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from clients.ironic import IronicClientError
from schemas.provision import ProvisionRequest
from schemas.server import ServerListResponse, ServerSummary
from services.provision import ProvisionService


class FakeNode:
    """Fake Ironic node for testing."""

    def __init__(self, name: str, node_id: str | None = None, provision_state: str = "available"):
        """Initialize fake node.

        Args:
            name: Node name
            node_id: Optional node UUID
            provision_state: Initial provision state
        """
        self.name = name
        self.id = node_id or str(uuid4())
        self.uuid = self.id
        self.driver = "redfish"
        self.driver_info = {}
        self.resource_class = "baremetal"
        self.properties = {"cpus": 16, "memory_mb": 65536}
        self.ports = []
        self.provision_state = provision_state
        self.network_data = None
        self.instance_info = None


class FakeIronicClientForProvision:
    """Test double for the Ironic client."""

    def __init__(self, node_id: str | None = None, simulate_error: str | None = None):
        """Initialize fake client.

        Args:
            node_id: Optional node UUID to simulate
            simulate_error: Error type to simulate ('ironic_error', 'not_found')
        """
        self.node_id = node_id or str(uuid4())
        self.node = FakeNode("test-server", self.node_id, "available")
        self.simulate_error = simulate_error
        self.set_instance_info_calls = []
        self.set_provision_state_calls = []

    async def get_node(self, node_id: str, ignore_missing: bool = False) -> FakeNode | None:
        """Get a node by ID."""
        if self.simulate_error == "ironic_error":
            raise IronicClientError("Failed to get node")

        if self.simulate_error == "not_found":
            if ignore_missing:
                return None
            raise IronicClientError(f"Node {node_id} not found")

        if node_id == self.node_id or node_id == self.node.id:
            return self.node

        if ignore_missing:
            return None

        raise IronicClientError(f"Node {node_id} not found")

    async def set_node_instance_info(
        self,
        node_id: str,
        instance_info: dict,
    ) -> FakeNode:
        """Set instance info for a node."""
        if self.simulate_error == "ironic_error":
            raise IronicClientError("Failed to set instance info")

        self.set_instance_info_calls.append((node_id, instance_info))
        self.node.instance_info = instance_info
        return self.node

    async def set_node_provision_state(
        self,
        node_id: str,
        target_state: str,
        configdrive: str | None = None,
    ) -> FakeNode:
        """Set node provision state target."""
        if self.simulate_error == "ironic_error":
            raise IronicClientError("Failed to set provision state")

        self.set_provision_state_calls.append((node_id, target_state, configdrive))
        self.node.provision_state = target_state
        return self.node


class FakeServerService:
    """Test double for the server service."""

    def __init__(self, available_servers: list[ServerSummary] | None = None):
        """Initialize fake server service.

        Args:
            available_servers: List of available servers
        """
        self.available_servers = available_servers or []

    async def list_servers(
        self,
        provision_state=None,
        resource_class=None,
        available_only=False,
        page=1,
        page_size=50
    ):
        """Return mocked list of servers."""
        servers = self.available_servers
        if resource_class:
            servers = [
                s for s in servers
                if s.resource_class == resource_class
            ]
        return ServerListResponse(
            servers=servers,
            total=len(servers),
            page=page,
            page_size=page_size
        )


@pytest.fixture()
def mock_ironic_client() -> FakeIronicClientForProvision:
    """Create a fake Ironic client."""
    return FakeIronicClientForProvision(node_id="test-server-uuid")


@pytest.fixture()
def available_server() -> ServerSummary:
    """Create a mock available server."""
    now = datetime.now(timezone.utc)
    return ServerSummary(
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


@pytest.fixture()
def fake_server_service_with_server(
    available_server: ServerSummary,
) -> FakeServerService:
    """Create a fake server service with available server."""
    return FakeServerService(available_servers=[available_server])


@pytest.fixture()
def fake_server_service_empty() -> FakeServerService:
    """Create a fake server service with no servers."""
    return FakeServerService()


@pytest.mark.asyncio
async def test_provision_server_with_specific_id(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test provisioning a specific server."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    request = ProvisionRequest(
        server_id="test-server-uuid",
        image_id="ubuntu-22.04"
    )

    result = await service.provision_server(request)

    assert result.server_id == "test-server-uuid"
    assert result.operation_id == "test-server-uuid"
    assert result.server_name == "test-server"
    assert result.status == "accepted"
    assert "provisioning" in result.message.lower()
    assert isinstance(result.started_at, datetime)


@pytest.mark.asyncio
async def test_provision_server_auto_select(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test provisioning with auto-selection."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    request = ProvisionRequest(
        image_id="ubuntu-22.04"
    )

    result = await service.provision_server(request)

    assert result.server_id == "test-server-uuid"
    assert result.status == "accepted"


@pytest.mark.asyncio
async def test_provision_server_auto_select_with_resource_class(
    mock_ironic_client: FakeIronicClientForProvision,
) -> None:
    """Test auto-selection with resource class filter."""
    now = datetime.now(timezone.utc)
    server = ServerSummary(
        id="gpu-server-uuid",
        name="gpu-server",
        provision_state="available",
        power_state="power on",
        resource_class="gpu-baremetal",
        is_available=True,
        properties={"gpus": 2},
        created_at=now,
        updated_at=now
    )
    fake_server_service = FakeServerService(available_servers=[server])

    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service
    )

    request = ProvisionRequest(
        image_id="ubuntu-22.04",
        resource_class="gpu-baremetal"
    )

    result = await service.provision_server(request)

    assert result.server_id == "gpu-server-uuid"


@pytest.mark.asyncio
async def test_provision_server_not_found(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_empty: FakeServerService,
) -> None:
    """Test provisioning fails when server not found."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_empty
    )

    request = ProvisionRequest(
        server_id="nonexistent-server",
        image_id="ubuntu-22.04"
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.provision_server(request)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_auto_select_no_available_servers(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_empty: FakeServerService,
) -> None:
    """Test auto-selection fails when no servers available."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_empty
    )

    request = ProvisionRequest(
        image_id="ubuntu-22.04"
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.provision_server(request)

    assert exc_info.value.status_code == 404
    assert "no available servers" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_provision_status(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test getting provision status."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    status = await service.get_provision_status("test-server-uuid")

    assert status.operation_id == "test-server-uuid"
    assert status.server_id == "test-server-uuid"
    assert status.status in ["in_progress", "completed", "failed"]
    assert status.provision_state is not None
    assert isinstance(status.started_at, datetime)


@pytest.mark.asyncio
async def test_get_provision_status_in_progress(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test provision status when deployment in progress."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    status = await service.get_provision_status("test-server-uuid")

    # Current mock returns deploying state
    assert status.status == "in_progress"
    assert status.progress_percent is not None


@pytest.mark.asyncio
async def test_validate_server_available_success(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test server availability validation succeeds."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    server_id = await service._validate_server_available("test-server-uuid")

    assert server_id == "test-server-uuid"


@pytest.mark.asyncio
async def test_validate_server_available_not_found(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_empty: FakeServerService,
) -> None:
    """Test server validation fails when not found."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_empty
    )

    with pytest.raises(HTTPException) as exc_info:
        await service._validate_server_available("nonexistent")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_auto_select_server_success(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test auto-selection succeeds."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    server_id = await service._auto_select_server()

    assert server_id == "test-server-uuid"


@pytest.mark.asyncio
async def test_select_server_with_specific_id(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test server selection with specific ID."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    request = ProvisionRequest(
        server_id="test-server-uuid",
        image_id="ubuntu-22.04"
    )

    server_id = await service._select_server(request)

    assert server_id == "test-server-uuid"

# Tests for real Ironic integration


@pytest.mark.asyncio
async def test_provision_server_calls_set_instance_info(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test that provision_server calls set_node_instance_info with image."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    request = ProvisionRequest(
        server_id="test-server-uuid",
        image_id="ubuntu-22.04"
    )

    await service.provision_server(request)

    # Verify set_node_instance_info was called
    assert len(mock_ironic_client.set_instance_info_calls) == 1
    node_id, instance_info = mock_ironic_client.set_instance_info_calls[0]
    assert node_id == "test-server-uuid"
    assert instance_info["image_source"] == "ubuntu-22.04"


@pytest.mark.asyncio
async def test_provision_server_calls_set_provision_state(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test that provision_server calls set_node_provision_state with active target."""
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    request = ProvisionRequest(
        server_id="test-server-uuid",
        image_id="ubuntu-22.04"
    )

    await service.provision_server(request)

    # Verify set_node_provision_state was called
    assert len(mock_ironic_client.set_provision_state_calls) == 1
    node_id, target_state, configdrive = mock_ironic_client.set_provision_state_calls[0]
    assert node_id == "test-server-uuid"
    assert target_state == "active"
    assert configdrive is None


@pytest.mark.asyncio
async def test_provision_server_with_config_drive(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test that config_drive is base64-encoded."""
    import base64
    import json

    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    config_data = {"hostname": "test-host", "ssh_keys": ["key1"]}
    request = ProvisionRequest(
        server_id="test-server-uuid",
        image_id="ubuntu-22.04",
        config_drive=config_data
    )

    await service.provision_server(request)

    # Verify config_drive was encoded
    assert len(mock_ironic_client.set_provision_state_calls) == 1
    node_id, target_state, configdrive = mock_ironic_client.set_provision_state_calls[0]
    
    assert configdrive is not None
    # Decode and verify
    decoded = base64.b64decode(configdrive).decode()
    decoded_data = json.loads(decoded)
    assert decoded_data == config_data


@pytest.mark.asyncio
async def test_get_provision_status_active_server(
    mock_ironic_client: FakeIronicClientForProvision,
) -> None:
    """Test provision status for active server."""
    # Set node to active state
    mock_ironic_client.node.provision_state = "active"

    fake_server_service = FakeServerService(available_servers=[])
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service
    )

    status = await service.get_provision_status("test-server-uuid")

    assert status.status == "completed"
    assert status.provision_state == "active"
    assert status.progress_percent == 100
    assert status.completed_at is not None


@pytest.mark.asyncio
async def test_get_provision_status_deploying_server(
    mock_ironic_client: FakeIronicClientForProvision,
) -> None:
    """Test provision status for deploying server."""
    # Set node to deploying state
    mock_ironic_client.node.provision_state = "deploying"

    fake_server_service = FakeServerService(available_servers=[])
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service
    )

    status = await service.get_provision_status("test-server-uuid")

    assert status.status == "in_progress"
    assert status.provision_state == "deploying"
    assert status.progress_percent == 50
    assert status.completed_at is None


@pytest.mark.asyncio
async def test_get_provision_status_failed_server(
    mock_ironic_client: FakeIronicClientForProvision,
) -> None:
    """Test provision status for failed server."""
    # Set node to deploy failed state
    mock_ironic_client.node.provision_state = "deploy failed"

    fake_server_service = FakeServerService(available_servers=[])
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service
    )

    status = await service.get_provision_status("test-server-uuid")

    assert status.status == "failed"
    assert status.provision_state == "deploy failed"
    assert status.progress_percent is None
    assert status.completed_at is not None


@pytest.mark.asyncio
async def test_get_provision_status_not_found(
    mock_ironic_client: FakeIronicClientForProvision,
) -> None:
    """Test provision status when node not found."""
    mock_ironic_client.simulate_error = "not_found"

    fake_server_service = FakeServerService(available_servers=[])
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_provision_status("nonexistent-server")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_provision_status_ironic_error(
    mock_ironic_client: FakeIronicClientForProvision,
) -> None:
    """Test provision status when Ironic API fails."""
    mock_ironic_client.simulate_error = "ironic_error"

    fake_server_service = FakeServerService(available_servers=[])
    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_provision_status("test-server-uuid")

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_provision_server_ironic_error(
    mock_ironic_client: FakeIronicClientForProvision,
    fake_server_service_with_server: FakeServerService,
) -> None:
    """Test provision_server when Ironic API fails."""
    mock_ironic_client.simulate_error = "ironic_error"

    service = ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_server
    )

    request = ProvisionRequest(
        server_id="test-server-uuid",
        image_id="ubuntu-22.04"
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.provision_server(request)

    assert exc_info.value.status_code == 502
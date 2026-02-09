"""Tests for the server service."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from schemas.server import ServerListResponse
from services.server import ServerService


class FakeIronicClientForServer:
    """Test double for the Ironic client."""

    def __init__(self, nodes: list[Mock] | None = None):
        """Initialize fake client.

        Args:
            nodes: List of fake Ironic node objects
        """
        self.nodes = nodes or []

    async def list_nodes(self) -> list[Mock]:
        """Return list of fake nodes."""
        return self.nodes

    async def get_node(self, node_id: str, ignore_missing: bool = False) -> Mock | None:
        """Get a specific node by ID or name."""
        for node in self.nodes:
            if node.uuid == node_id or node.name == node_id:
                return node
        if ignore_missing:
            return None
        return None


def create_fake_node(
    uuid: str,
    name: str,
    provision_state: str = "available",
    power_state: str = "power off",
    resource_class: str = "baremetal",
    maintenance: bool = False,
    properties: dict | None = None
) -> Mock:
    """Create a fake Ironic node for testing.

    Args:
        uuid: Node UUID
        name: Node name
        provision_state: Current provisioning state
        power_state: Current power state
        resource_class: Resource classification
        maintenance: Whether node is in maintenance mode
        properties: Node properties dictionary

    Returns:
        Mock node object with required attributes
    """
    node = Mock()
    node.uuid = uuid
    node.name = name
    node.provision_state = provision_state
    node.power_state = power_state
    node.resource_class = resource_class
    node.maintenance = maintenance
    node.properties = properties or {}
    node.created_at = datetime.now(timezone.utc)
    node.updated_at = datetime.now(timezone.utc)
    return node


@pytest.fixture()
def fake_ironic_client_empty() -> FakeIronicClientForServer:
    """Create a fake Ironic client with no nodes."""
    return FakeIronicClientForServer()


@pytest.fixture()
def fake_ironic_client_with_servers() -> FakeIronicClientForServer:
    """Create a fake Ironic client with multiple servers."""
    nodes = [
        create_fake_node(
            uuid="node-1",
            name="server-1",
            provision_state="available",
            power_state="power off"
        ),
        create_fake_node(
            uuid="node-2",
            name="server-2",
            provision_state="active",
            power_state="power on",
            resource_class="baremetal"
        ),
        create_fake_node(
            uuid="node-3",
            name="server-3",
            provision_state="available",
            power_state="power off",
            resource_class="storage"
        ),
    ]
    return FakeIronicClientForServer(nodes=nodes)


@pytest.mark.asyncio
async def test_list_servers_empty(
    fake_ironic_client_empty: FakeIronicClientForServer,
) -> None:
    """Test listing servers when none exist."""
    service = ServerService(ironic_client=fake_ironic_client_empty)

    result = await service.list_servers()

    assert isinstance(result, ServerListResponse)
    assert result.total == 0
    assert len(result.servers) == 0
    assert result.page == 1
    assert result.page_size == 50


@pytest.mark.asyncio
async def test_list_servers_success(
    fake_ironic_client_with_servers: FakeIronicClientForServer,
) -> None:
    """Test listing all servers successfully."""
    service = ServerService(ironic_client=fake_ironic_client_with_servers)

    result = await service.list_servers()

    assert isinstance(result, ServerListResponse)
    assert result.total == 3
    assert len(result.servers) == 3
    assert result.page == 1
    assert result.page_size == 50


@pytest.mark.asyncio
async def test_list_servers_with_pagination(
    fake_ironic_client_with_servers: FakeIronicClientForServer,
) -> None:
    """Test listing servers with custom pagination."""
    service = ServerService(ironic_client=fake_ironic_client_with_servers)

    result = await service.list_servers(page=1, page_size=2)

    assert result.page == 1
    assert result.page_size == 2
    assert len(result.servers) == 2


@pytest.mark.asyncio
async def test_list_servers_filter_by_provision_state(
    fake_ironic_client_with_servers: FakeIronicClientForServer,
) -> None:
    """Test filtering servers by provision state."""
    service = ServerService(ironic_client=fake_ironic_client_with_servers)

    result = await service.list_servers(provision_state="available")

    assert isinstance(result, ServerListResponse)
    assert result.total == 2
    assert {server.id for server in result.servers} == {"node-1", "node-3"}


@pytest.mark.asyncio
async def test_list_servers_filter_by_resource_class(
    fake_ironic_client_with_servers: FakeIronicClientForServer,
) -> None:
    """Test filtering servers by resource class."""
    service = ServerService(ironic_client=fake_ironic_client_with_servers)

    result = await service.list_servers(resource_class="baremetal")

    assert isinstance(result, ServerListResponse)
    assert result.total == 2
    assert {server.id for server in result.servers} == {"node-1", "node-2"}


@pytest.mark.asyncio
async def test_list_servers_available_only(
    fake_ironic_client_with_servers: FakeIronicClientForServer,
) -> None:
    """Test filtering for available servers only."""
    service = ServerService(ironic_client=fake_ironic_client_with_servers)

    result = await service.list_servers(available_only=True)

    assert isinstance(result, ServerListResponse)
    assert result.total == 2
    assert {server.id for server in result.servers} == {"node-1", "node-3"}


@pytest.mark.asyncio
async def test_get_server_not_found(
    fake_ironic_client_empty: FakeIronicClientForServer,
) -> None:
    """Test getting a server that doesn't exist."""
    service = ServerService(ironic_client=fake_ironic_client_empty)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_server("nonexistent-server")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_server_by_uuid(
    fake_ironic_client_with_servers: FakeIronicClientForServer,
) -> None:
    """Test getting a server by UUID."""
    service = ServerService(ironic_client=fake_ironic_client_with_servers)

    result = await service.get_server("node-1")

    assert result.id == "node-1"
    assert result.name == "server-1"


@pytest.mark.asyncio
async def test_get_server_by_name(
    fake_ironic_client_with_servers: FakeIronicClientForServer,
) -> None:
    """Test getting a server by name."""
    service = ServerService(ironic_client=fake_ironic_client_with_servers)

    result = await service.get_server("server-1")

    assert result.id == "node-1"
    assert result.name == "server-1"


def test_is_available_available_state() -> None:
    """Test availability check for available server."""
    service = ServerService(ironic_client=FakeIronicClientForServer())

    node = create_fake_node(
        uuid="node-1",
        name="server-1",
        provision_state="available",
        power_state="power off",
        maintenance=False
    )

    result = service._is_available(node)
    assert result is True


def test_is_available_in_maintenance() -> None:
    """Test availability check for server in maintenance."""
    service = ServerService(ironic_client=FakeIronicClientForServer())

    node = create_fake_node(
        uuid="node-1",
        name="server-1",
        provision_state="available",
        power_state="power off",
        maintenance=True
    )

    result = service._is_available(node)
    assert result is False


def test_is_available_power_on() -> None:
    """Test availability check for powered-on server."""
    service = ServerService(ironic_client=FakeIronicClientForServer())

    node = create_fake_node(
        uuid="node-1",
        name="server-1",
        provision_state="available",
        power_state="power on",
        maintenance=False
    )

    result = service._is_available(node)
    assert result is False


def test_is_available_active_provision_state() -> None:
    """Test availability check for server with active provision state."""
    service = ServerService(ironic_client=FakeIronicClientForServer())

    node = create_fake_node(
        uuid="node-1",
        name="server-1",
        provision_state="active",
        power_state="power on",
        maintenance=False
    )

    result = service._is_available(node)
    assert result is False

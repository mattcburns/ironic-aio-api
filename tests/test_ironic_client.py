"""Tests for the Ironic client wrapper."""

import pytest

import httpx
from openstack import exceptions as os_exceptions

from clients.ironic import IronicClient, IronicClientError
from config import Settings


class ConnectionSpy:
    """Capture connection arguments for assertions."""

    def __init__(self) -> None:
        self.called = False
        self.kwargs = {}

    def __call__(self, **kwargs):  # type: ignore[override]
        self.called = True
        self.kwargs = kwargs
        return object()


@pytest.mark.asyncio
async def test_get_connection_uses_noauth(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = ConnectionSpy()
    monkeypatch.setattr("clients.ironic.os_connection.Connection", spy)
    # Clear any .env loaded credentials and CA skip settings
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_SKIP_CA_VERIFICATION", raising=False)

    settings = Settings(
        ironic_basic_auth_username=None,
        ironic_basic_auth_password=None,
        ironic_skip_ca_verification=False,
    )
    client = IronicClient(settings)
    connection = await client.get_connection()

    assert spy.called is True
    assert connection is not None
    assert spy.kwargs["auth_type"] == "none"
    assert spy.kwargs["endpoint_override"] == settings.ironic_api_url
    assert spy.kwargs["baremetal_endpoint_override"] == settings.ironic_api_url
    assert spy.kwargs["baremetal_api_version"] == settings.ironic_api_version
    assert spy.kwargs["verify"] is True


def test_get_http_client_auth_returns_none_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Clear any .env loaded credentials
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_PASSWORD", raising=False)

    settings = Settings(
        ironic_basic_auth_username=None,
        ironic_basic_auth_password=None,
    )
    client = IronicClient(settings)

    auth = client._get_http_client_auth()

    assert auth is None


def test_get_http_client_auth_returns_basic_auth_with_credentials() -> None:
    settings = Settings(
        ironic_basic_auth_username="testuser",
        ironic_basic_auth_password="testpass",
    )
    client = IronicClient(settings)

    auth = client._get_http_client_auth()

    assert isinstance(auth, httpx.BasicAuth)


def test_create_http_client_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Clear any .env loaded credentials
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_SKIP_CA_VERIFICATION", raising=False)

    settings = Settings(
        ironic_skip_ca_verification=False,
        ironic_basic_auth_username=None,
        ironic_basic_auth_password=None,
    )
    client = IronicClient(settings)

    # Verify the client can be created successfully without auth
    http_client = client._create_http_client()
    assert isinstance(http_client, httpx.AsyncClient)
    assert http_client._auth is None


def test_create_http_client_with_credentials() -> None:
    settings = Settings(
        ironic_basic_auth_username="testuser",
        ironic_basic_auth_password="testpass",
        ironic_skip_ca_verification=True,
    )
    client = IronicClient(settings)

    # Verify the client can be created successfully with auth
    http_client = client._create_http_client()
    assert isinstance(http_client, httpx.AsyncClient)
    assert http_client._auth is not None


@pytest.mark.asyncio
async def test_get_connection_uses_basic_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = ConnectionSpy()
    monkeypatch.setattr("clients.ironic.os_connection.Connection", spy)

    settings = Settings(
        ironic_basic_auth_username="ironic-user",
        ironic_basic_auth_password="ironic-pass",
        ironic_skip_ca_verification=True,
    )
    client = IronicClient(settings)
    connection = await client.get_connection()

    assert spy.called is True
    assert connection is not None
    assert spy.kwargs["auth_type"] == "http_basic"
    assert spy.kwargs["auth"] == {
        "username": "ironic-user",
        "password": "ironic-pass",
    }
    assert spy.kwargs["verify"] is False


@pytest.mark.asyncio
async def test_check_connectivity_returns_false_on_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_error():
        raise IronicClientError("boom")

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", raise_error)

    assert await client.check_connectivity() is False


@pytest.mark.asyncio
async def test_check_connectivity_returns_true_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def succeed():
        return object()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", succeed)

    assert await client.check_connectivity() is True


@pytest.mark.asyncio
async def test_list_nodes_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test listing nodes successfully."""
    # Mock connection and nodes
    class MockNode:
        pass

    mock_nodes = [MockNode(), MockNode()]

    class MockBaremetal:
        def nodes(self):
            return iter(mock_nodes)

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    nodes = await client.list_nodes()

    assert len(nodes) == 2
    assert nodes[0] is mock_nodes[0]
    assert nodes[1] is mock_nodes[1]


@pytest.mark.asyncio
async def test_list_nodes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test list_nodes raises IronicClientError on failure."""

    class MockBaremetal:
        def nodes(self):
            raise RuntimeError("API error")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    with pytest.raises(IronicClientError, match="Failed to list Ironic nodes"):
        await client.list_nodes()


@pytest.mark.asyncio
async def test_get_node_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting a node by ID successfully."""

    class MockNode:
        id = "node-123"
        name = "test-node"

    class MockBaremetal:
        def get_node(self, node_id):
            return MockNode()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    node = await client.get_node("node-123")

    assert node.id == "node-123"
    assert node.name == "test-node"


@pytest.mark.asyncio
async def test_get_node_ignore_missing_with_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ignore_missing works when SDK does not accept the parameter."""

    class MockNode:
        id = "node-123"
        name = "test-node"

    class MockBaremetal:
        def get_node(self, node_id):
            return MockNode()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    node = await client.get_node("node-123", ignore_missing=True)

    assert node is not None
    assert node.id == "node-123"


@pytest.mark.asyncio
async def test_get_node_ignore_missing_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ignore_missing returns None when node is missing."""

    class MockBaremetal:
        def get_node(self, node_id):
            raise os_exceptions.ResourceNotFound("not found")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    node = await client.get_node("node-123", ignore_missing=True)

    assert node is None


@pytest.mark.asyncio
async def test_get_node_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_node raises IronicClientError on failure."""

    class MockBaremetal:
        def get_node(self, node_id):
            raise RuntimeError("Node not found")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    with pytest.raises(IronicClientError, match="Failed to get node node-123"):
        await client.get_node("node-123")


@pytest.mark.asyncio
async def test_get_node_by_name_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting a node by name successfully."""

    class MockNode:
        id = "node-456"
        name = "server-01"

    class MockBaremetal:
        def find_node(self, name, ignore_missing=False):
            return MockNode()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    node = await client.get_node_by_name("server-01")

    assert node is not None
    assert node.id == "node-456"
    assert node.name == "server-01"


@pytest.mark.asyncio
async def test_get_node_by_name_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting a node by name when it doesn't exist."""

    class MockBaremetal:
        def find_node(self, name, ignore_missing=False):
            return None

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    node = await client.get_node_by_name("nonexistent")

    assert node is None


@pytest.mark.asyncio
async def test_get_node_by_name_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_node_by_name raises IronicClientError on failure."""

    class MockBaremetal:
        def find_node(self, name, ignore_missing=False):
            raise RuntimeError("API error")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    with pytest.raises(IronicClientError, match="Failed to get node by name test"):
        await client.get_node_by_name("test")


@pytest.mark.asyncio
async def test_create_node_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test creating a node successfully."""

    class MockNode:
        id = "new-node-789"
        name = "new-server"

    class MockBaremetal:
        def create_node(self, **kwargs):
            return MockNode()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    node = await client.create_node(
        name="new-server",
        driver="redfish",
        driver_info={"address": "https://bmc.example.com"},
        resource_class="baremetal",
        properties={"cpu": 4},
    )

    assert node.id == "new-node-789"
    assert node.name == "new-server"


@pytest.mark.asyncio
async def test_create_node_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test creating a node with minimal parameters."""

    created_kwargs = {}

    class MockNode:
        id = "minimal-node"
        name = "minimal"

    class MockBaremetal:
        def create_node(self, **kwargs):
            nonlocal created_kwargs
            created_kwargs = kwargs
            return MockNode()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    node = await client.create_node(
        name="minimal",
        driver="ipmi",
        driver_info={"address": "10.0.0.1"},
    )

    assert node.name == "minimal"
    assert created_kwargs["name"] == "minimal"
    assert created_kwargs["driver"] == "ipmi"
    assert "resource_class" not in created_kwargs
    assert "properties" not in created_kwargs


@pytest.mark.asyncio
async def test_create_node_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test create_node raises IronicClientError on failure."""

    class MockBaremetal:
        def create_node(self, **kwargs):
            raise RuntimeError("Duplicate name")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    with pytest.raises(IronicClientError, match="Failed to create node test-server"):
        await client.create_node(
            name="test-server",
            driver="redfish",
            driver_info={},
        )


@pytest.mark.asyncio
async def test_add_node_port_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test adding a port to a node successfully."""

    class MockPort:
        uuid = "port-123"
        address = "aa:bb:cc:dd:ee:ff"

    class MockBaremetal:
        def create_port(self, **kwargs):
            return MockPort()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    port = await client.add_node_port(
        node_id="node-999",
        mac_address="aa:bb:cc:dd:ee:ff",
        extra={"nic_name": "eth0"},
    )

    assert port.uuid == "port-123"
    assert port.address == "aa:bb:cc:dd:ee:ff"


@pytest.mark.asyncio
async def test_add_node_port_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test adding a port with minimal parameters."""

    created_kwargs = {}

    class MockPort:
        uuid = "port-456"

    class MockBaremetal:
        def create_port(self, **kwargs):
            nonlocal created_kwargs
            created_kwargs = kwargs
            return MockPort()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    port = await client.add_node_port(
        node_id="node-888",
        mac_address="11:22:33:44:55:66",
    )

    assert port.uuid == "port-456"
    assert created_kwargs["node_uuid"] == "node-888"
    assert created_kwargs["address"] == "11:22:33:44:55:66"
    assert "extra" not in created_kwargs


@pytest.mark.asyncio
async def test_add_node_port_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test add_node_port raises IronicClientError on failure."""

    class MockBaremetal:
        def create_port(self, **kwargs):
            raise RuntimeError("Invalid MAC address")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    with pytest.raises(IronicClientError, match="Failed to add port to node node-777"):
        await client.add_node_port(
            node_id="node-777",
            mac_address="invalid",
        )


@pytest.mark.asyncio
async def test_validate_node_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validating a node successfully."""
    validation_result = {
        "power": {"result": True},
        "management": {"result": True},
    }

    class MockBaremetal:
        def validate_node(self, node_id):
            return validation_result

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    result = await client.validate_node("node-abc")

    assert result == validation_result


@pytest.mark.asyncio
async def test_validate_node_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validate_node raises IronicClientError on failure."""

    class MockBaremetal:
        def validate_node(self, node_id):
            raise RuntimeError("Node not found")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    with pytest.raises(IronicClientError, match="Failed to validate node node-xyz"):
        await client.validate_node("node-xyz")

@pytest.mark.asyncio
async def test_set_node_provision_state_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test set_node_provision_state successfully transitions node state."""

    class FakeNode:
        id = "node-123"
        provision_state = "manage"

    class MockBaremetal:
        def set_node_provision_state(self, node_id, target_state):
            return FakeNode()

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    result = await client.set_node_provision_state("node-123", "manage")

    assert result.id == "node-123"
    assert result.provision_state == "manage"


@pytest.mark.asyncio
async def test_set_node_provision_state_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test set_node_provision_state raises IronicClientError on failure."""

    class MockBaremetal:
        def set_node_provision_state(self, node_id, target_state):
            raise RuntimeError("State transition failed")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    with pytest.raises(IronicClientError, match="Failed to set provision state"):
        await client.set_node_provision_state("node-123", "manage")


@pytest.mark.asyncio
async def test_set_node_network_data_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test set_node_network_data successfully sets network data on node."""

    class FakeNode:
        id = "node-456"
        network_data = {
            "links": [{"id": "port-123", "type": "phy", "ethernet_mac_address": "aa:bb:cc:dd:ee:ff"}],
            "networks": [{"id": "network0", "type": "ipv4", "ip_address": "10.0.0.10"}],
            "services": []
        }

    class MockBaremetal:
        def patch_node(self, node_id, patch):
            """Mock patch_node to apply network_data patch."""
            node = FakeNode()
            # Apply the patch
            for operation in patch:
                if operation["op"] == "add" and operation["path"] == "/network_data":
                    node.network_data = operation["value"]
            return node

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    network_data = {
        "links": [{"id": "port-123", "type": "phy", "ethernet_mac_address": "aa:bb:cc:dd:ee:ff"}],
        "networks": [{"id": "network0", "type": "ipv4", "ip_address": "10.0.0.10"}],
        "services": []
    }
    result = await client.set_node_network_data("node-456", network_data)

    assert result.id == "node-456"
    assert result.network_data is not None
    assert result.network_data["links"][0]["ethernet_mac_address"] == "aa:bb:cc:dd:ee:ff"


@pytest.mark.asyncio
async def test_set_node_network_data_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test set_node_network_data raises IronicClientError on failure."""

    class MockBaremetal:
        def patch_node(self, node_id, patch):
            raise RuntimeError("Network data patch failed")

    class MockConnection:
        baremetal = MockBaremetal()

    async def mock_get_connection():
        return MockConnection()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", mock_get_connection)

    network_data = {"links": [], "networks": [], "services": []}
    with pytest.raises(IronicClientError, match="Failed to set network data"):
        await client.set_node_network_data("node-456", network_data)



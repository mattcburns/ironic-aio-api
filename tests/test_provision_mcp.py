"""Tests for the provision MCP tool."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

import pytest

from mcp_tools.provision import provision_server, check_provision_status
from schemas.server import ServerListResponse, ServerSummary
from services.provision import ProvisionService


class FakeNode:
    """Fake Ironic node for testing."""

    def __init__(self, name: str, node_id: str | None = None, provision_state: str = "available"):
        """Initialize fake node."""
        self.name = name
        self.id = node_id or str(uuid4())
        self.uuid = self.id
        self.driver = "redfish"
        self.driver_info = {}
        self.resource_class = "baremetal"
        self.properties = {"cpus": 16, "memory_mb": 65536}
        self.provision_state = provision_state
        self.instance_info = None


class FakeIronicClientForMCP:
    """Fake Ironic client for MCP tests."""

    def __init__(self):
        """Initialize fake client."""
        self.node = FakeNode("test-server", "test-server-uuid", "available")

    async def get_node(self, node_id: str, ignore_missing: bool = False) -> FakeNode | None:
        """Get a node by ID."""
        if node_id == "test-server-uuid" or node_id == self.node.id:
            return self.node
        if ignore_missing:
            return None
        raise Exception(f"Node {node_id} not found")

    async def set_node_instance_info(self, node_id: str, instance_info: dict) -> FakeNode:
        """Set instance info for a node."""
        self.node.instance_info = instance_info
        return self.node

    async def set_node_provision_state(self, node_id: str, target_state: str, configdrive: str | None = None) -> FakeNode:
        """Set node provision state target."""
        self.node.provision_state = target_state
        return self.node


class FakeServerService:
    """Fake server service for MCP tests."""

    def __init__(self, available_servers: list[ServerSummary] | None = None):
        """Initialize fake server service."""
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
def mock_server_service(available_server: ServerSummary) -> FakeServerService:
    """Create a mock server service."""
    return FakeServerService(available_servers=[available_server])


@pytest.fixture()
def mock_ironic_client() -> FakeIronicClientForMCP:
    """Create a mock ironic client."""
    return FakeIronicClientForMCP()


@pytest.fixture()
def mock_provision_service(mock_ironic_client: FakeIronicClientForMCP, mock_server_service: FakeServerService) -> ProvisionService:
    """Create a provision service with mocked dependencies."""
    return ProvisionService(
        ironic_client=mock_ironic_client,
        server_service=mock_server_service
    )


@pytest.mark.asyncio
async def test_provision_server_mcp_tool_success(mock_provision_service) -> None:
    """Test successful provisioning via MCP tool."""
    from dependencies import get_provision_service
    from app import app
    
    def override_get_provision_service():
        return mock_provision_service

    app.dependency_overrides[get_provision_service] = override_get_provision_service
    
    try:
        result = await provision_server(
            image_id="ubuntu-22.04",
            server_id="test-server-uuid"
        )
        
        assert result["server_id"] == "test-server-uuid"
        assert result["operation_id"] == "test-server-uuid"
        assert result["status"] == "accepted"
        assert "message" in result
        assert "started_at" in result
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_provision_server_mcp_tool_auto_select(mock_provision_service) -> None:
    """Test provisioning with auto-selection via MCP tool."""
    from dependencies import get_provision_service
    from app import app
    
    def override_get_provision_service():
        return mock_provision_service

    app.dependency_overrides[get_provision_service] = override_get_provision_service
    
    try:
        result = await provision_server(
            image_id="ubuntu-22.04"
        )
        
        assert "operation_id" in result
        assert result["status"] == "accepted"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_provision_server_mcp_tool_with_resource_class(mock_provision_service) -> None:
    """Test provisioning with resource class via MCP tool."""
    from dependencies import get_provision_service
    from app import app
    
    def override_get_provision_service():
        return mock_provision_service

    app.dependency_overrides[get_provision_service] = override_get_provision_service
    
    try:
        result = await provision_server(
            image_id="ubuntu-22.04",
            resource_class="baremetal"
        )
        
        assert result["status"] == "accepted"
        assert "operation_id" in result
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_check_provision_status_mcp_tool(mock_provision_service) -> None:
    """Test checking provision status via MCP tool."""
    from dependencies import get_provision_service
    from app import app
    
    def override_get_provision_service():
        return mock_provision_service

    app.dependency_overrides[get_provision_service] = override_get_provision_service
    
    try:
        result = await check_provision_status(
            operation_id="test-server-uuid"
        )
        
        assert result["operation_id"] == "test-server-uuid"
        assert result["server_id"] == "test-server-uuid"
        assert "status" in result
        assert "provision_state" in result
        assert "message" in result
        assert "started_at" in result
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_check_provision_status_mcp_tool_structure(mock_provision_service) -> None:
    """Test provision status response structure from MCP tool."""
    from dependencies import get_provision_service
    from app import app
    
    def override_get_provision_service():
        return mock_provision_service

    app.dependency_overrides[get_provision_service] = override_get_provision_service
    
    try:
        result = await check_provision_status(
            operation_id="test-server-uuid"
        )
        
        # Verify all required fields
        assert "operation_id" in result
        assert "server_id" in result
        assert "status" in result
        assert "provision_state" in result
        assert "message" in result
        assert "started_at" in result
        
        # Status should be one of the expected values
        assert result["status"] in ["in_progress", "completed", "failed"]
    finally:
        app.dependency_overrides.clear()

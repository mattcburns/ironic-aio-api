"""Tests for the unprovision service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from clients.ironic import IronicClientError
from schemas.server import ServerSummary
from schemas.unprovision import UnprovisionRequest
from services.unprovision import UnprovisionService


class FakeNode:
    """Fake Ironic node for testing."""

    def __init__(
        self,
        node_id: str,
        provision_state: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        """Initialize fake node.

        Args:
            node_id: Node UUID
            provision_state: Current provision state
            created_at: Node creation timestamp
            updated_at: Node update timestamp
        """
        self.id = node_id
        self.provision_state = provision_state
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)


class FakeServerService:
    """Test double for the server service."""

    def __init__(self, server: ServerSummary | None = None):
        """Initialize fake server service.

        Args:
            server: Server to return from get_server
        """
        self.server = server

    async def get_server(self, server_id: str):
        """Return mocked server."""
        if self.server is None:
            raise HTTPException(status_code=404, detail="Server not found")
        return self.server


@pytest.fixture()
def mock_ironic_client() -> AsyncMock:
    """Create a mock Ironic client."""
    return AsyncMock()


@pytest.fixture()
def active_server() -> ServerSummary:
    """Create a mock active server."""
    now = datetime.now(timezone.utc)
    return ServerSummary(
        id="test-server-uuid",
        name="test-server",
        provision_state="active",
        power_state="power on",
        resource_class="baremetal",
        is_available=False,
        properties={"cpus": 16, "memory_mb": 65536},
        created_at=now,
        updated_at=now
    )


@pytest.fixture()
def available_server() -> ServerSummary:
    """Create a mock available server."""
    now = datetime.now(timezone.utc)
    return ServerSummary(
        id="available-server-uuid",
        name="available-server",
        provision_state="available",
        power_state="power off",
        resource_class="baremetal",
        is_available=True,
        properties={"cpus": 8, "memory_mb": 32768},
        created_at=now,
        updated_at=now
    )


@pytest.fixture()
def fake_server_service_with_active_server(
    active_server: ServerSummary,
) -> FakeServerService:
    """Create a fake server service with active server."""
    return FakeServerService(server=active_server)


@pytest.fixture()
def fake_server_service_with_available_server(
    available_server: ServerSummary,
) -> FakeServerService:
    """Create a fake server service with available server."""
    return FakeServerService(server=available_server)


@pytest.fixture()
def fake_server_service_empty() -> FakeServerService:
    """Create a fake server service with no server."""
    return FakeServerService()


@pytest.mark.asyncio
async def test_unprovision_server_success(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test successful server unprovisioning."""
    # Setup mock to succeed
    mock_ironic_client.set_node_provision_state = AsyncMock(return_value=None)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    request = UnprovisionRequest(
        server_id="test-server-uuid",
        clean=True
    )

    result = await service.unprovision_server(request)

    assert result.server_id == "test-server-uuid"
    assert result.server_name == "test-server"
    assert result.status == "accepted"
    assert "unprovisioning" in result.message.lower()
    assert isinstance(result.started_at, datetime)

    # Verify Ironic was called with correct target
    mock_ironic_client.set_node_provision_state.assert_called_once_with(
        node_id="test-server-uuid",
        target_state="deleted"
    )


@pytest.mark.asyncio
async def test_unprovision_server_without_clean(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test unprovisioning without cleaning."""
    # Setup mock to succeed
    mock_ironic_client.set_node_provision_state = AsyncMock(return_value=None)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    request = UnprovisionRequest(
        server_id="test-server-uuid",
        clean=False
    )

    result = await service.unprovision_server(request)

    assert result.server_id == "test-server-uuid"
    assert result.status == "accepted"

    # Verify Ironic was called with "available" target
    mock_ironic_client.set_node_provision_state.assert_called_once_with(
        node_id="test-server-uuid",
        target_state="available"
    )


@pytest.mark.asyncio
async def test_unprovision_server_not_found(
    mock_ironic_client: AsyncMock,
    fake_server_service_empty: FakeServerService,
) -> None:
    """Test unprovisioning fails when server not found."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_empty
    )

    request = UnprovisionRequest(
        server_id="nonexistent-server",
        clean=True
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.unprovision_server(request)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_unprovision_server_not_in_provisionable_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_available_server: FakeServerService,
) -> None:
    """Test unprovisioning fails when server not in provisionable state."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_available_server
    )

    request = UnprovisionRequest(
        server_id="available-server-uuid",
        clean=True
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.unprovision_server(request)

    assert exc_info.value.status_code == 409
    assert "not in a provisionable state" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_unprovision_status(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test getting unprovision status."""
    # Setup mock to return a node in cleaning state
    now = datetime.now(timezone.utc)
    fake_node = FakeNode(
        node_id="test-server-uuid",
        provision_state="cleaning",
        created_at=now,
        updated_at=now
    )
    mock_ironic_client.get_node = AsyncMock(return_value=fake_node)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    status = await service.get_unprovision_status("test-server-uuid")

    assert status.server_id == "test-server-uuid"
    assert status.status in ["in_progress", "completed", "failed"]
    assert status.provision_state is not None
    assert isinstance(status.started_at, datetime)

    # Verify Ironic was called
    mock_ironic_client.get_node.assert_called_once_with(
        "test-server-uuid",
        ignore_missing=True
    )


@pytest.mark.asyncio
async def test_get_unprovision_status_in_progress(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test unprovision status when cleaning in progress."""
    # Setup mock to return a node in cleaning state
    now = datetime.now(timezone.utc)
    fake_node = FakeNode(
        node_id="test-server-uuid",
        provision_state="cleaning",
        created_at=now,
        updated_at=now
    )
    mock_ironic_client.get_node = AsyncMock(return_value=fake_node)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    status = await service.get_unprovision_status("test-server-uuid")

    # Current mock returns cleaning state
    assert status.status == "in_progress"
    assert status.progress_percent is not None


@pytest.mark.asyncio
async def test_validate_server_provisionable_active_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test validation passes for active server."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    # Should not raise
    await service._validate_server_provisionable("test-server-uuid", "active")


@pytest.mark.asyncio
async def test_validate_server_provisionable_deploy_failed_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test validation passes for deploy failed server."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    # Should not raise
    await service._validate_server_provisionable("test-server-uuid", "deploy failed")


@pytest.mark.asyncio
async def test_validate_server_provisionable_error_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test validation passes for error server."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    # Should not raise
    await service._validate_server_provisionable("test-server-uuid", "error")


@pytest.mark.asyncio
async def test_validate_server_provisionable_fails_for_available(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_available_server: FakeServerService,
) -> None:
    """Test validation fails for available server."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_available_server
    )

    with pytest.raises(HTTPException) as exc_info:
        await service._validate_server_provisionable("available-server-uuid", "available")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_get_server_by_id_success(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
    active_server: ServerSummary,
) -> None:
    """Test getting server by ID succeeds."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    server = await service._get_server_by_id("test-server-uuid")

    assert server.id == active_server.id
    assert server.name == active_server.name


@pytest.mark.asyncio
async def test_get_server_by_id_not_found(
    mock_ironic_client: AsyncMock,
    fake_server_service_empty: FakeServerService,
) -> None:
    """Test getting server by ID fails when not found."""
    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_empty
    )

    with pytest.raises(HTTPException) as exc_info:
        await service._get_server_by_id("nonexistent")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_unprovision_server_ironic_error(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test unprovisioning handles Ironic client errors."""
    # Setup mock to raise IronicClientError
    mock_ironic_client.set_node_provision_state = AsyncMock(
        side_effect=IronicClientError("Ironic API error")
    )

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    request = UnprovisionRequest(
        server_id="test-server-uuid",
        clean=True
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.unprovision_server(request)

    assert exc_info.value.status_code == 502
    assert "Failed to communicate with Ironic" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_unprovision_status_node_not_found(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test status check handles node not found."""
    # Setup mock to return None (node not found)
    mock_ironic_client.get_node = AsyncMock(return_value=None)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_unprovision_status("nonexistent-server")

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_unprovision_status_ironic_error(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test status check handles Ironic client errors."""
    # Setup mock to raise IronicClientError
    mock_ironic_client.get_node = AsyncMock(
        side_effect=IronicClientError("Ironic API error")
    )

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_unprovision_status("test-server-uuid")

    assert exc_info.value.status_code == 502
    assert "Failed to communicate with Ironic" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_unprovision_status_deleting_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test status mapping for deleting state."""
    now = datetime.now(timezone.utc)
    fake_node = FakeNode(
        node_id="test-server-uuid",
        provision_state="deleting",
        created_at=now,
        updated_at=now
    )
    mock_ironic_client.get_node = AsyncMock(return_value=fake_node)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    status = await service.get_unprovision_status("test-server-uuid")

    assert status.status == "in_progress"
    assert status.provision_state == "deleting"
    assert status.progress_percent == 75
    assert status.completed_at is None


@pytest.mark.asyncio
async def test_get_unprovision_status_available_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test status mapping for available (completed) state."""
    now = datetime.now(timezone.utc)
    fake_node = FakeNode(
        node_id="test-server-uuid",
        provision_state="available",
        created_at=now,
        updated_at=now
    )
    mock_ironic_client.get_node = AsyncMock(return_value=fake_node)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    status = await service.get_unprovision_status("test-server-uuid")

    assert status.status == "completed"
    assert status.provision_state == "available"
    assert status.progress_percent == 100
    assert status.completed_at is not None


@pytest.mark.asyncio
async def test_get_unprovision_status_clean_failed_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test status mapping for clean failed state."""
    now = datetime.now(timezone.utc)
    fake_node = FakeNode(
        node_id="test-server-uuid",
        provision_state="clean failed",
        created_at=now,
        updated_at=now
    )
    mock_ironic_client.get_node = AsyncMock(return_value=fake_node)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    status = await service.get_unprovision_status("test-server-uuid")

    assert status.status == "failed"
    assert status.provision_state == "clean failed"
    assert status.progress_percent is None
    assert status.completed_at is not None


@pytest.mark.asyncio
async def test_get_unprovision_status_error_state(
    mock_ironic_client: AsyncMock,
    fake_server_service_with_active_server: FakeServerService,
) -> None:
    """Test status mapping for error state."""
    now = datetime.now(timezone.utc)
    fake_node = FakeNode(
        node_id="test-server-uuid",
        provision_state="error",
        created_at=now,
        updated_at=now
    )
    mock_ironic_client.get_node = AsyncMock(return_value=fake_node)

    service = UnprovisionService(
        ironic_client=mock_ironic_client,
        server_service=fake_server_service_with_active_server
    )

    status = await service.get_unprovision_status("test-server-uuid")

    assert status.status == "failed"
    assert status.provision_state == "error"
    assert status.progress_percent is None
    assert status.completed_at is not None


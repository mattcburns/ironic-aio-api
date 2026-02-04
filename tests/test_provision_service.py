"""Tests for the provision service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from schemas.provision import ProvisionRequest
from schemas.server import ServerListResponse, ServerSummary
from services.provision import ProvisionService


class FakeIronicClientForProvision:
    """Test double for the Ironic client."""

    def __init__(self):
        """Initialize fake client."""
        pass


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
    return FakeIronicClientForProvision()


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

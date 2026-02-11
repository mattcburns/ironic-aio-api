"""Tests for the unprovision MCP tool."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_tools.unprovision import unprovision_server, check_unprovision_status
from schemas.server import ServerSummary
from schemas.unprovision import UnprovisionResponse, UnprovisionStatus


@pytest.fixture()
def mock_active_server():
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
def mock_server_service(mock_active_server):
    """Create a mock server service."""
    service = MagicMock()
    service.get_server = AsyncMock(return_value=mock_active_server)
    return service


@pytest.fixture()
def mock_unprovision_service():
    """Create a mock unprovision service."""
    service = MagicMock()
    now = datetime.now(timezone.utc)

    # Mock unprovision_server method
    service.unprovision_server = AsyncMock(
        return_value=UnprovisionResponse(
            server_id="test-server-uuid",
            server_name="test-server",
            status="accepted",
            message="Unprovisioning of test-server initiated",
            started_at=now
        )
    )

    # Mock get_unprovision_status method
    service.get_unprovision_status = AsyncMock(
        return_value=UnprovisionStatus(
            server_id="test-server-uuid",
            status="in_progress",
            provision_state="cleaning",
            progress_percent=50,
            message="Unprovisioning status: cleaning",
            started_at=now,
            completed_at=None
        )
    )

    return service


@pytest.mark.asyncio
async def test_unprovision_server_mcp_tool_success(mock_unprovision_service) -> None:
    """Test successful unprovisioning via MCP tool."""
    with patch('mcp_tools.unprovision.get_unprovision_service', return_value=mock_unprovision_service):
        result = await unprovision_server(
            server_id="test-server-uuid",
            clean=True
        )

    assert result["server_id"] == "test-server-uuid"
    assert result["status"] == "accepted"
    assert "message" in result
    assert "started_at" in result


@pytest.mark.asyncio
async def test_unprovision_server_mcp_tool_without_clean(mock_unprovision_service) -> None:
    """Test unprovisioning without cleaning via MCP tool."""
    with patch('mcp_tools.unprovision.get_unprovision_service', return_value=mock_unprovision_service):
        result = await unprovision_server(
            server_id="test-server-uuid",
            clean=False
        )

    assert result["server_id"] == "test-server-uuid"
    assert result["status"] == "accepted"


@pytest.mark.asyncio
async def test_unprovision_server_mcp_tool_default_clean(mock_unprovision_service) -> None:
    """Test unprovisioning defaults to clean=True."""
    with patch('mcp_tools.unprovision.get_unprovision_service', return_value=mock_unprovision_service):
        result = await unprovision_server(
            server_id="test-server-uuid"
        )

    assert result["status"] == "accepted"


@pytest.mark.asyncio
async def test_check_unprovision_status_mcp_tool(mock_unprovision_service) -> None:
    """Test checking unprovision status via MCP tool."""
    with patch('mcp_tools.unprovision.get_unprovision_service', return_value=mock_unprovision_service):
        result = await check_unprovision_status(
            server_id="test-server-uuid"
        )

    assert result["server_id"] == "test-server-uuid"
    assert "status" in result
    assert "provision_state" in result
    assert "message" in result
    assert "started_at" in result


@pytest.mark.asyncio
async def test_check_unprovision_status_mcp_tool_structure(mock_unprovision_service) -> None:
    """Test unprovision status response structure from MCP tool."""
    with patch('mcp_tools.unprovision.get_unprovision_service', return_value=mock_unprovision_service):
        result = await check_unprovision_status(
            server_id="test-server-uuid"
        )

    # Verify all required fields
    assert "server_id" in result
    assert "status" in result
    assert "provision_state" in result
    assert "message" in result
    assert "started_at" in result

    # Status should be one of the expected values
    assert result["status"] in ["in_progress", "completed", "failed"]

"""Tests for the provision MCP tool."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from mcp_tools.provision import provision_server, check_provision_status
from schemas.server import ServerListResponse, ServerSummary


@pytest.fixture()
def mock_server_service():
    """Create a mock server service."""
    service = MagicMock()
    now = datetime.now(timezone.utc)
    server = ServerSummary(
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
    response = ServerListResponse(
        servers=[server],
        total=1,
        page=1,
        page_size=50
    )
    service.list_servers = AsyncMock(return_value=response)
    return service


@pytest.mark.asyncio
async def test_provision_server_mcp_tool_success(mock_server_service) -> None:
    """Test successful provisioning via MCP tool."""
    with patch('dependencies.get_server_service', return_value=mock_server_service):
        result = await provision_server(
            image_id="ubuntu-22.04",
            server_id="test-server-uuid"
        )

    assert result["server_id"] == "test-server-uuid"
    assert result["operation_id"] == "test-server-uuid"
    assert result["status"] == "accepted"
    assert "message" in result
    assert "started_at" in result


@pytest.mark.asyncio
async def test_provision_server_mcp_tool_auto_select(mock_server_service) -> None:
    """Test provisioning with auto-selection via MCP tool."""
    with patch('dependencies.get_server_service', return_value=mock_server_service):
        result = await provision_server(
            image_id="ubuntu-22.04"
        )

    assert "operation_id" in result
    assert result["status"] == "accepted"


@pytest.mark.asyncio
async def test_provision_server_mcp_tool_with_resource_class(mock_server_service) -> None:
    """Test provisioning with resource class via MCP tool."""
    with patch('dependencies.get_server_service', return_value=mock_server_service):
        result = await provision_server(
            image_id="ubuntu-22.04",
            resource_class="baremetal"
        )

    assert result["status"] == "accepted"
    assert "operation_id" in result


@pytest.mark.asyncio
async def test_check_provision_status_mcp_tool() -> None:
    """Test checking provision status via MCP tool."""
    result = await check_provision_status(
        operation_id="test-server-uuid"
    )

    assert result["operation_id"] == "test-server-uuid"
    assert result["server_id"] == "test-server-uuid"
    assert "status" in result
    assert "provision_state" in result
    assert "message" in result
    assert "started_at" in result


@pytest.mark.asyncio
async def test_check_provision_status_mcp_tool_structure() -> None:
    """Test provision status response structure from MCP tool."""
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

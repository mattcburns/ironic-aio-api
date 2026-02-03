"""Tests for the server MCP tools."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from schemas.server import ServerListResponse, ServerSummary


@pytest.mark.asyncio
async def test_list_servers_mcp_tool() -> None:
    """Test list_servers MCP tool returns correct format."""
    from mcp_tools.server import list_servers

    # Mock the service
    with patch("mcp_tools.server.get_server_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Mock response
        mock_response = ServerListResponse(
            servers=[],
            total=0,
            page=1,
            page_size=50
        )
        mock_service.list_servers.return_value = mock_response

        result = await list_servers()

        assert isinstance(result, dict)
        assert "servers" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result


@pytest.mark.asyncio
async def test_list_servers_mcp_tool_with_filters() -> None:
    """Test list_servers MCP tool with filters."""
    from mcp_tools.server import list_servers

    # Mock the service
    with patch("mcp_tools.server.get_server_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Mock response
        mock_response = ServerListResponse(
            servers=[],
            total=0,
            page=1,
            page_size=50
        )
        mock_service.list_servers.return_value = mock_response

        result = await list_servers(
            provision_state="available",
            resource_class="baremetal",
            available_only=True
        )

        # Verify service was called with correct arguments
        mock_service.list_servers.assert_called_once()
        args, kwargs = mock_service.list_servers.call_args
        assert kwargs.get("provision_state") == "available"
        assert kwargs.get("resource_class") == "baremetal"
        assert kwargs.get("available_only") is True

        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_get_server_mcp_tool() -> None:
    """Test get_server MCP tool returns correct format."""
    from mcp_tools.server import get_server

    # Mock the service
    with patch("mcp_tools.server.get_server_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Mock response
        mock_response = ServerSummary(
            id="node-1",
            name="test-server",
            provision_state="available",
            power_state="power off",
            resource_class="baremetal",
            is_available=True,
            properties={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_service.get_server.return_value = mock_response

        result = await get_server("node-1")

        assert isinstance(result, dict)
        assert result["id"] == "node-1"
        assert result["name"] == "test-server"
        assert "provision_state" in result
        assert "power_state" in result
        assert "resource_class" in result
        assert "is_available" in result


@pytest.mark.asyncio
async def test_get_server_mcp_tool_calls_service() -> None:
    """Test get_server MCP tool calls service with correct argument."""
    from mcp_tools.server import get_server

    # Mock the service
    with patch("mcp_tools.server.get_server_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Mock response
        mock_response = ServerSummary(
            id="node-1",
            name="test-server",
            provision_state="available",
            power_state="power off",
            resource_class="baremetal",
            is_available=True,
            properties={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_service.get_server.return_value = mock_response

        await get_server("my-server-name")

        # Verify service was called with correct argument
        mock_service.get_server.assert_called_once_with("my-server-name")


@pytest.mark.asyncio
async def test_list_servers_mcp_tool_returns_serializable_dict() -> None:
    """Test that list_servers returns a serializable dictionary."""
    from mcp_tools.server import list_servers

    # Mock the service
    with patch("mcp_tools.server.get_server_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Create mock servers
        mock_servers = [
            ServerSummary(
                id="node-1",
                name="server-1",
                provision_state="available",
                power_state="power off",
                resource_class="baremetal",
                is_available=True,
                properties={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]

        # Mock response
        mock_response = ServerListResponse(
            servers=mock_servers,
            total=1,
            page=1,
            page_size=50
        )
        mock_service.list_servers.return_value = mock_response

        result = await list_servers()

        # Verify it's a proper dictionary
        assert isinstance(result, dict)
        assert result["total"] == 1
        assert len(result["servers"]) == 1
        assert result["servers"][0]["id"] == "node-1"

        # Verify datetime is present (model_dump() keeps datetime objects)
        # For actual JSON serialization, FastAPI will handle conversion
        assert "created_at" in result["servers"][0]


@pytest.mark.asyncio
async def test_get_server_mcp_tool_returns_serializable_dict() -> None:
    """Test that get_server returns a serializable dictionary."""
    from mcp_tools.server import get_server

    # Mock the service
    with patch("mcp_tools.server.get_server_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Mock response
        mock_response = ServerSummary(
            id="node-1",
            name="test-server",
            provision_state="available",
            power_state="power off",
            resource_class="baremetal",
            is_available=True,
            properties={"cpu": "Intel Xeon"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_service.get_server.return_value = mock_response

        result = await get_server("test-server")

        # Verify it's a proper dictionary
        assert isinstance(result, dict)
        assert result["name"] == "test-server"

        # Verify datetime fields are present (model_dump() keeps datetime objects)
        # For actual JSON serialization, FastAPI will handle conversion
        assert "created_at" in result
        assert "updated_at" in result

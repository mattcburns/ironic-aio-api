"""Tests for the health MCP tool."""

import pytest

from config import get_settings
from mcp_tools import health as health_tool
from services.health import HealthService
from tests.conftest import FakeIronicClient


@pytest.mark.asyncio
async def test_health_mcp_tool_returns_status(
    fake_ironic_client_connected: FakeIronicClient,
) -> None:
    settings = get_settings()
    original_get_health_service = health_tool.get_health_service
    health_tool.get_health_service = lambda: HealthService(
        settings=settings,
        ironic_client=fake_ironic_client_connected,
    )

    payload = await health_tool.check_health()

    health_tool.get_health_service = original_get_health_service

    assert payload["status"] == "healthy"
    assert payload["version"] == settings.app_version
    assert "timestamp" in payload
    assert payload["ironic_connected"] is True
    assert payload["ironic_api_version"] == settings.ironic_api_version


@pytest.mark.asyncio
async def test_health_mcp_tool_degraded_when_ironic_down(
    fake_ironic_client_disconnected: FakeIronicClient,
) -> None:
    settings = get_settings()
    original_get_health_service = health_tool.get_health_service
    health_tool.get_health_service = lambda: HealthService(
        settings=settings,
        ironic_client=fake_ironic_client_disconnected,
    )

    payload = await health_tool.check_health()

    health_tool.get_health_service = original_get_health_service

    assert payload["status"] == "degraded"
    assert payload["ironic_connected"] is False
    assert payload["ironic_api_version"] is None

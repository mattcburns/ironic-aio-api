"""Tests for the health service."""

import pytest

from config import get_settings
from services.health import HealthService
from tests.conftest import FakeIronicClient


@pytest.mark.asyncio
async def test_health_service_returns_status(
    fake_ironic_client_connected: FakeIronicClient,
) -> None:
    settings = get_settings()
    service = HealthService(
        settings=settings,
        ironic_client=fake_ironic_client_connected,
    )
    result = await service.check_health()

    assert result.status == "healthy"
    assert result.version == settings.app_version
    assert result.timestamp.tzinfo is not None
    assert result.ironic_connected is True
    assert result.ironic_api_version == settings.ironic_api_version


@pytest.mark.asyncio
async def test_health_service_degraded_when_ironic_down(
    fake_ironic_client_disconnected: FakeIronicClient,
) -> None:
    settings = get_settings()
    service = HealthService(
        settings=settings,
        ironic_client=fake_ironic_client_disconnected,
    )
    result = await service.check_health()

    assert result.status == "degraded"
    assert result.ironic_connected is False
    assert result.ironic_api_version is None

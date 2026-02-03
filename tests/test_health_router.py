"""Tests for the health router."""

from fastapi.testclient import TestClient

from app import app
from config import get_settings
from services.health import HealthService, get_health_service
from tests.conftest import FakeIronicClient


def test_health_endpoint_returns_status(
    client: TestClient,
    fake_ironic_client_connected: FakeIronicClient,
) -> None:
    settings = get_settings()
    app.dependency_overrides[get_health_service] = lambda: HealthService(
        settings=settings,
        ironic_client=fake_ironic_client_connected,
    )
    response = client.get("/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == settings.app_version
    assert "timestamp" in payload
    assert payload["ironic_connected"] is True
    assert payload["ironic_api_version"] == settings.ironic_api_version


def test_health_endpoint_degraded_when_ironic_down(
    client: TestClient,
    fake_ironic_client_disconnected: FakeIronicClient,
) -> None:
    settings = get_settings()
    app.dependency_overrides[get_health_service] = lambda: HealthService(
        settings=settings,
        ironic_client=fake_ironic_client_disconnected,
    )
    response = client.get("/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["ironic_connected"] is False
    assert payload["ironic_api_version"] is None

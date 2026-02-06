"""Pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app import app
from dependencies import get_enroll_service
from services.enroll import EnrollService
from tests.test_enroll_service import FakeIronicClientForEnroll


class FakeIronicClient:
    """Test double for the Ironic client."""

    def __init__(self, connected: bool) -> None:
        self._connected = connected

    async def check_connectivity(self) -> bool:
        return self._connected


@pytest.fixture()
def client() -> TestClient:
    """Create a FastAPI test client with mocked enrollment dependencies."""
    fake_ironic_client = FakeIronicClientForEnroll()

    def override_get_enroll_service():
        return EnrollService(ironic_client=fake_ironic_client)

    app.dependency_overrides[get_enroll_service] = override_get_enroll_service

    test_client = TestClient(app)

    # Clear overrides after test
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def fake_ironic_client_connected() -> FakeIronicClient:
    """Create a fake Ironic client that reports as connected."""
    return FakeIronicClient(connected=True)


@pytest.fixture()
def fake_ironic_client_disconnected() -> FakeIronicClient:
    """Create a fake Ironic client that reports as disconnected."""
    return FakeIronicClient(connected=False)


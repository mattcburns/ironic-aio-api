"""Pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app import app


class FakeIronicClient:
    """Test double for the Ironic client."""

    def __init__(self, connected: bool) -> None:
        self._connected = connected

    async def check_connectivity(self) -> bool:
        return self._connected


@pytest.fixture()
def client() -> TestClient:
    """Create a FastAPI test client."""

    return TestClient(app)


@pytest.fixture()
def fake_ironic_client_connected() -> FakeIronicClient:
    """Create a fake Ironic client that reports as connected."""
    return FakeIronicClient(connected=True)


@pytest.fixture()
def fake_ironic_client_disconnected() -> FakeIronicClient:
    """Create a fake Ironic client that reports as disconnected."""
    return FakeIronicClient(connected=False)

"""Pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app import app
from dependencies import get_enroll_service, get_provision_service
from services.enroll import EnrollService
from services.provision import ProvisionService
from tests.test_enroll_service import FakeIronicClientForEnroll
from tests.test_provision_service import FakeIronicClientForProvision, FakeServerService
from schemas.server import ServerSummary
from datetime import datetime, timezone


class FakeIronicClient:
    """Test double for the Ironic client."""

    def __init__(self, connected: bool) -> None:
        self._connected = connected

    async def check_connectivity(self) -> bool:
        return self._connected


@pytest.fixture()
def client() -> TestClient:
    """Create a FastAPI test client with mocked enrollment and provision dependencies."""
    fake_ironic_client_enroll = FakeIronicClientForEnroll()
    fake_ironic_client_provision = FakeIronicClientForProvision(node_id="test-server-uuid")
    
    # Create test server for provision tests
    now = datetime.now(timezone.utc)
    test_server = ServerSummary(
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
    fake_server_service = FakeServerService(available_servers=[test_server])

    def override_get_enroll_service():
        return EnrollService(ironic_client=fake_ironic_client_enroll)

    def override_get_provision_service():
        return ProvisionService(
            ironic_client=fake_ironic_client_provision,
            server_service=fake_server_service
        )

    app.dependency_overrides[get_enroll_service] = override_get_enroll_service
    app.dependency_overrides[get_provision_service] = override_get_provision_service

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


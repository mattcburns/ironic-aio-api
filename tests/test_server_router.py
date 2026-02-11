"""Tests for the server router."""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import app
from dependencies import get_server_service
from schemas.server import ServerListResponse, ServerSummary


class FakeServerService:
    """Test double for server service."""

    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self._servers = [
            ServerSummary(
                id="node-1",
                name="server-1",
                provision_state="available",
                power_state="power off",
                resource_class="baremetal",
                is_available=True,
                properties={},
                created_at=now,
                updated_at=now,
            )
        ]

    async def list_servers(
        self,
        provision_state=None,
        resource_class=None,
        available_only=False,
        page=1,
        page_size=50,
    ) -> ServerListResponse:
        servers = self._servers
        if provision_state:
            servers = [server for server in servers if server.provision_state == provision_state]
        if resource_class:
            servers = [server for server in servers if server.resource_class == resource_class]
        if available_only:
            servers = [server for server in servers if server.is_available]
        total = len(servers)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_servers = servers[start_idx:end_idx]
        return ServerListResponse(
            servers=paginated_servers,
            total=total,
            page=page,
            page_size=page_size
        )

    async def get_server(self, server_id: str) -> ServerSummary:
        """Get a server by ID."""
        for server in self._servers:
            if server.id == server_id:
                return server
        raise HTTPException(
            status_code=404,
            detail=f"Server '{server_id}' not found"
        )
        return ServerListResponse(
            servers=servers[start_idx:end_idx],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_server(self, server_id: str) -> ServerSummary:
        for server in self._servers:
            if server.id == server_id or server.name == server_id:
                return server
        raise HTTPException(status_code=404, detail="Server not found")


@pytest.fixture()
def client() -> TestClient:
    """Create a FastAPI test client with server service overrides."""
    fake_service = FakeServerService()

    def override_get_server_service():
        return fake_service

    app.dependency_overrides[get_server_service] = override_get_server_service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


class TestListServers:
    """Tests for the list servers endpoint."""

    def test_list_servers_default_pagination(self, client: TestClient) -> None:
        """Test listing servers with default pagination."""
        response = client.get("/servers")

        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_list_servers_custom_pagination(self, client: TestClient) -> None:
        """Test listing servers with custom pagination."""
        response = client.get("/servers?page=2&page_size=25")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 25

    def test_list_servers_page_size_max(self, client: TestClient) -> None:
        """Test listing servers with maximum page size."""
        response = client.get("/servers?page_size=100")

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 100

    def test_list_servers_page_size_exceeds_max(self, client: TestClient) -> None:
        """Test that page size cannot exceed maximum."""
        response = client.get("/servers?page_size=101")

        # Should fail validation
        assert response.status_code == 422

    def test_list_servers_invalid_page(self, client: TestClient) -> None:
        """Test that page must be >= 1."""
        response = client.get("/servers?page=0")

        # Should fail validation
        assert response.status_code == 422

    def test_list_servers_filter_by_provision_state(self, client: TestClient) -> None:
        """Test filtering servers by provision state."""
        response = client.get("/servers?provision_state=available")

        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_list_servers_filter_by_resource_class(self, client: TestClient) -> None:
        """Test filtering servers by resource class."""
        response = client.get("/servers?resource_class=baremetal")

        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_list_servers_available_only(self, client: TestClient) -> None:
        """Test filtering for available servers only."""
        response = client.get("/servers?available_only=true")

        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_list_servers_combined_filters(self, client: TestClient) -> None:
        """Test listing servers with multiple filters combined."""
        response = client.get(
            "/servers?provision_state=available&resource_class=baremetal&available_only=true&page=1&page_size=25"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 25


class TestGetServer:
    """Tests for the get server endpoint."""

    def test_get_server_by_id(self, client: TestClient) -> None:
        """Test getting a server by UUID."""
        response = client.get("/servers/node-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "node-1"
        assert data["name"] == "server-1"

    def test_get_server_by_name(self, client: TestClient) -> None:
        """Test getting a server by name."""
        response = client.get("/servers/server-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "node-1"
        assert data["name"] == "server-1"

    def test_get_server_response_schema(self, client: TestClient) -> None:
        """Test that server endpoint returns the response schema."""
        response = client.get("/servers/server-1")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "provision_state" in data
        assert "is_available" in data
        assert "created_at" in data


class TestServerEndpointOpenAPI:
    """Tests for OpenAPI documentation of server endpoints."""

    def test_openapi_includes_list_servers(self, client: TestClient) -> None:
        """Test that OpenAPI spec includes list_servers endpoint."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi = response.json()
        assert "/servers" in openapi["paths"]

    def test_openapi_includes_get_server(self, client: TestClient) -> None:
        """Test that OpenAPI spec includes get_server endpoint."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi = response.json()
        assert "/servers/{server_id}" in openapi["paths"]

    def test_openapi_list_servers_has_filters(self, client: TestClient) -> None:
        """Test that OpenAPI spec documents list_servers filters."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi = response.json()
        list_endpoint = openapi["paths"]["/servers"]["get"]

        # Check for query parameters
        params = {p["name"] for p in list_endpoint.get("parameters", [])}
        assert "provision_state" in params
        assert "resource_class" in params
        assert "available_only" in params
        assert "page" in params
        assert "page_size" in params

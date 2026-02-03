"""Tests for the server router."""

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture()
def client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


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
        # This will fail until Ironic client calls are implemented
        # The service raises NotImplementedError which propagates
        with pytest.raises(NotImplementedError):
            client.get("/servers/node-uuid-12345")

    def test_get_server_by_name(self, client: TestClient) -> None:
        """Test getting a server by name."""
        # This will fail until Ironic client calls are implemented
        # The service raises NotImplementedError which propagates
        with pytest.raises(NotImplementedError):
            client.get("/servers/test-server")

    def test_get_server_response_schema(self, client: TestClient) -> None:
        """Test that server endpoint raises when not implemented."""
        # Until Ironic API calls are implemented, expect NotImplementedError
        with pytest.raises(NotImplementedError):
            client.get("/servers/test-server")


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

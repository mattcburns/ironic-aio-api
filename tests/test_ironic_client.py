"""Tests for the Ironic client wrapper."""

import pytest

import httpx

from clients.ironic import IronicClient, IronicClientError
from config import Settings


class ConnectionSpy:
    """Capture connection arguments for assertions."""

    def __init__(self) -> None:
        self.called = False
        self.kwargs = {}

    def __call__(self, **kwargs):  # type: ignore[override]
        self.called = True
        self.kwargs = kwargs
        return object()


@pytest.mark.asyncio
async def test_get_connection_uses_noauth(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = ConnectionSpy()
    monkeypatch.setattr("clients.ironic.os_connection.Connection", spy)
    # Clear any .env loaded credentials and CA skip settings
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_SKIP_CA_VERIFICATION", raising=False)

    settings = Settings(
        ironic_basic_auth_username=None,
        ironic_basic_auth_password=None,
        ironic_skip_ca_verification=False,
    )
    client = IronicClient(settings)
    connection = await client.get_connection()

    assert spy.called is True
    assert connection is not None
    assert spy.kwargs["auth_type"] == "none"
    assert spy.kwargs["endpoint_override"] == settings.ironic_api_url
    assert spy.kwargs["baremetal_endpoint_override"] == settings.ironic_api_url
    assert spy.kwargs["baremetal_api_version"] == settings.ironic_api_version
    assert spy.kwargs["verify"] is True


def test_get_http_client_auth_returns_none_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Clear any .env loaded credentials
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_PASSWORD", raising=False)

    settings = Settings(
        ironic_basic_auth_username=None,
        ironic_basic_auth_password=None,
    )
    client = IronicClient(settings)

    auth = client._get_http_client_auth()

    assert auth is None


def test_get_http_client_auth_returns_basic_auth_with_credentials() -> None:
    settings = Settings(
        ironic_basic_auth_username="testuser",
        ironic_basic_auth_password="testpass",
    )
    client = IronicClient(settings)

    auth = client._get_http_client_auth()

    assert isinstance(auth, httpx.BasicAuth)


def test_create_http_client_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Clear any .env loaded credentials
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_BASIC_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("IRONIC_AIO_IRONIC_SKIP_CA_VERIFICATION", raising=False)

    settings = Settings(
        ironic_skip_ca_verification=False,
        ironic_basic_auth_username=None,
        ironic_basic_auth_password=None,
    )
    client = IronicClient(settings)

    # Verify the client can be created successfully without auth
    http_client = client._create_http_client()
    assert isinstance(http_client, httpx.AsyncClient)
    assert http_client._auth is None


def test_create_http_client_with_credentials() -> None:
    settings = Settings(
        ironic_basic_auth_username="testuser",
        ironic_basic_auth_password="testpass",
        ironic_skip_ca_verification=True,
    )
    client = IronicClient(settings)

    # Verify the client can be created successfully with auth
    http_client = client._create_http_client()
    assert isinstance(http_client, httpx.AsyncClient)
    assert http_client._auth is not None


@pytest.mark.asyncio
async def test_get_connection_uses_basic_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = ConnectionSpy()
    monkeypatch.setattr("clients.ironic.os_connection.Connection", spy)

    settings = Settings(
        ironic_basic_auth_username="ironic-user",
        ironic_basic_auth_password="ironic-pass",
        ironic_skip_ca_verification=True,
    )
    client = IronicClient(settings)
    connection = await client.get_connection()

    assert spy.called is True
    assert connection is not None
    assert spy.kwargs["auth_type"] == "http_basic"
    assert spy.kwargs["auth"] == {
        "username": "ironic-user",
        "password": "ironic-pass",
    }
    assert spy.kwargs["verify"] is False


@pytest.mark.asyncio
async def test_check_connectivity_returns_false_on_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_error():
        raise IronicClientError("boom")

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", raise_error)

    assert await client.check_connectivity() is False


@pytest.mark.asyncio
async def test_check_connectivity_returns_true_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def succeed():
        return object()

    settings = Settings()
    client = IronicClient(settings)
    monkeypatch.setattr(client, "get_connection", succeed)

    assert await client.check_connectivity() is True


@pytest.mark.asyncio
async def test_list_nodes_not_implemented() -> None:
    settings = Settings()
    client = IronicClient(settings)

    with pytest.raises(NotImplementedError):
        await client.list_nodes()


@pytest.mark.asyncio
async def test_get_node_not_implemented() -> None:
    settings = Settings()
    client = IronicClient(settings)

    with pytest.raises(NotImplementedError):
        await client.get_node("node-1")

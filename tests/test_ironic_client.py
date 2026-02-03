"""Tests for the Ironic client wrapper."""

import pytest

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

    settings = Settings()
    client = IronicClient(settings)
    connection = await client.get_connection()

    assert spy.called is True
    assert connection is not None
    assert spy.kwargs["auth_type"] == "none"
    assert spy.kwargs["endpoint_override"] == settings.ironic_api_url
    assert spy.kwargs["baremetal_endpoint_override"] == settings.ironic_api_url
    assert spy.kwargs["baremetal_api_version"] == settings.ironic_api_version


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

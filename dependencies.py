"""Dependency helpers."""

from clients.ironic import IronicClient
from config import Settings, get_settings


def get_ironic_client(settings: Settings | None = None) -> IronicClient:
    """Create an Ironic client instance."""

    if settings is None:
        settings = get_settings()
    return IronicClient(settings)

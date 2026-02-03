"""Health check service implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from clients.ironic import IronicClient
from config import Settings, get_settings
from dependencies import get_ironic_client
from schemas.health import HealthStatus


class HealthService:
    """Health check service shared by REST and MCP."""

    def __init__(self, settings: Settings, ironic_client: IronicClient) -> None:
        self._settings = settings
        self._ironic_client = ironic_client

    async def check_health(self) -> HealthStatus:
        """Check the health of the API and its dependencies."""

        ironic_connected = await self._ironic_client.check_connectivity()
        status = "healthy" if ironic_connected else "degraded"

        return HealthStatus(
            status=status,
            version=self._settings.app_version,
            timestamp=datetime.now(timezone.utc),
            ironic_connected=ironic_connected,
            ironic_api_version=self._settings.ironic_api_version
            if ironic_connected
            else None,
        )


def get_health_service() -> HealthService:
    """Create a health service instance."""

    settings = get_settings()
    ironic_client = get_ironic_client(settings)
    return HealthService(settings, ironic_client)

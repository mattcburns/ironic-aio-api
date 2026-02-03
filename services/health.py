# Copyright (C) 2026 Matthew Burns
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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

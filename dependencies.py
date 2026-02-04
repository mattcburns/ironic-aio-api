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

"""Dependency helpers."""

from clients.ironic import IronicClient
from config import Settings, get_settings


def get_ironic_client(settings: Settings | None = None) -> IronicClient:
    """Create an Ironic client instance."""

    if settings is None:
        settings = get_settings()
    return IronicClient(settings)


def get_enroll_service() -> "EnrollService":
    """Create an enrollment service instance."""
    from services.enroll import EnrollService

    ironic_client = get_ironic_client()
    return EnrollService(ironic_client)


def get_server_service() -> "ServerService":
    """Create a server service instance."""
    from services.server import ServerService

    ironic_client = get_ironic_client()
    return ServerService(ironic_client)

def get_provision_service() -> "ProvisionService":
    """Create a provision service instance."""
    from services.provision import ProvisionService

    ironic_client = get_ironic_client()
    server_service = get_server_service()
    return ProvisionService(ironic_client, server_service)


def get_unprovision_service() -> "UnprovisionService":
    """Create an unprovision service instance."""
    from services.unprovision import UnprovisionService

    ironic_client = get_ironic_client()
    server_service = get_server_service()
    return UnprovisionService(ironic_client, server_service)

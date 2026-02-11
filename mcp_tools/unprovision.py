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

from app import mcp
from dependencies import get_unprovision_service
from schemas.unprovision import UnprovisionRequest


@mcp.tool()
async def unprovision_server(server_id: str, clean: bool = True) -> dict:
    """
    Unprovision a server, returning it to available state.

    Args:
        server_id: The server ID or name to unprovision
        clean: Whether to run cleaning/wiping steps (default: True)

    Returns:
        Operation details including ID for status tracking
    """
    service = get_unprovision_service()
    request = UnprovisionRequest(
        server_id=server_id,
        clean=clean
    )
    result = await service.unprovision_server(request)
    return result.model_dump()


@mcp.tool()
async def check_unprovision_status(server_id: str) -> dict:
    """
    Check the status of a server unprovisioning operation.

    Args:
        server_id: The server ID (Ironic node UUID)

    Returns:
        Current unprovisioning status
    """
    service = get_unprovision_service()
    result = await service.get_unprovision_status(server_id)
    return result.model_dump()

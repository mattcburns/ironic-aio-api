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

from typing import Optional

from app import mcp
from dependencies import get_server_service


@mcp.tool()
async def list_servers(
    provision_state: Optional[str] = None,
    resource_class: Optional[str] = None,
    available_only: bool = False
) -> dict:
    """
    List all servers managed by Ironic.

    Args:
        provision_state: Filter by provisioning state (e.g., 'available', 'active')
        resource_class: Filter by resource class (e.g., 'baremetal')
        available_only: Only show servers available for provisioning

    Returns:
        List of servers with their current status including:
        - Server ID and name
        - Provisioning state
        - Power state
        - Resource class
        - Availability status
        - Server properties (CPU, memory, disk info)
    """
    service = get_server_service()
    result = await service.list_servers(
        provision_state=provision_state,
        resource_class=resource_class,
        available_only=available_only
    )
    return result.model_dump()


@mcp.tool()
async def get_server(server_id: str) -> dict:
    """
    Get detailed information about a specific server.

    Args:
        server_id: The server ID or name

    Returns:
        Server details including:
        - Server ID and name
        - Provisioning state and power state
        - Resource class
        - Availability status
        - Server properties (CPU, memory, disk info)
        - Creation and update timestamps
    """
    service = get_server_service()
    result = await service.get_server(server_id)
    return result.model_dump()

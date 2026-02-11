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
from dependencies import get_provision_service
from schemas.provision import ProvisionRequest


@mcp.tool()
async def provision_server(
    image_source: str,
    server_id: Optional[str] = None,
    resource_class: Optional[str] = None,
    image_checksum: Optional[str] = None
) -> dict:
    """
    Provision a server with an operating system image.

    Args:
        image_source: The image source URL, Glance image UUID, or image ID to deploy
        server_id: Specific server to provision (optional)
        resource_class: Auto-select server of this class if server_id not provided
        image_checksum: Optional MD5 or SHA checksum for image verification

    Returns:
        Operation details including ID for status tracking
    """
    service = get_provision_service()
    request = ProvisionRequest(
        server_id=server_id,
        resource_class=resource_class,
        image_source=image_source,
        image_checksum=image_checksum
    )
    result = await service.provision_server(request)
    return result.model_dump()


@mcp.tool()
async def check_provision_status(operation_id: str) -> dict:
    """
    Check the status of a server provisioning operation.

    Args:
        operation_id: The operation ID returned from provision_server

    Returns:
        Current provisioning status and progress
    """
    service = get_provision_service()
    result = await service.get_provision_status(operation_id)
    return result.model_dump()

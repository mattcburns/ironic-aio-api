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

from fastapi import APIRouter, Depends

from dependencies import get_provision_service
from schemas.provision import ProvisionRequest, ProvisionResponse, ProvisionStatus
from services.provision import ProvisionService

router = APIRouter(prefix="/provision", tags=["provisioning"])


@router.post("", response_model=ProvisionResponse, status_code=202)
async def provision_server(
    request: ProvisionRequest,
    service: ProvisionService = Depends(get_provision_service)
) -> ProvisionResponse:
    """
    Provision a server with the specified image.

    Initiates provisioning of a specific server or auto-selects an available server.
    Returns 202 Accepted with server ID for tracking.

    Args:
        request: Provisioning request with server selection and image details
        service: Provision service dependency

    Returns:
        ProvisionResponse with server ID for tracking

    Raises:
        HTTPException: 404 if server not found, 400 if image invalid, 502 if Ironic unreachable
    """
    return await service.provision_server(request)


@router.get("/{server_id}", response_model=ProvisionStatus)
async def get_provision_status(
    server_id: str,
    service: ProvisionService = Depends(get_provision_service)
) -> ProvisionStatus:
    """
    Get the status of a provisioning operation.

    Returns current provisioning status derived from Ironic's provision_state.

    Args:
        server_id: The server ID returned from provision_server
        service: Provision service dependency

    Returns:
        ProvisionStatus with current provisioning status and progress

    Raises:
        HTTPException: 404 if operation not found, 502 if Ironic unreachable
    """
    return await service.get_provision_status(server_id)

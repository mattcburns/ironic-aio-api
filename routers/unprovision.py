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

from dependencies import get_unprovision_service
from schemas.unprovision import UnprovisionRequest, UnprovisionResponse, UnprovisionStatus
from services.unprovision import UnprovisionService

router = APIRouter(prefix="/unprovision", tags=["unprovisioning"])


@router.post("", response_model=UnprovisionResponse, status_code=202)
async def unprovision_server(
    request: UnprovisionRequest,
    service: UnprovisionService = Depends(get_unprovision_service)
) -> UnprovisionResponse:
    """
    Unprovision a server, returning it to available state.

    Initiates unprovisioning of a server, optionally running cleaning/wiping steps.
    Returns 202 Accepted with operation ID for tracking.

    Args:
        request: Unprovisioning request with server ID
        service: Unprovision service dependency

    Returns:
        UnprovisionResponse with operation ID for tracking

    Raises:
        HTTPException: 404 if server not found, 409 if not in provisionable state, 502 if Ironic unreachable
    """
    return await service.unprovision_server(request)


@router.get("/{operation_id}", response_model=UnprovisionStatus)
async def get_unprovision_status(
    operation_id: str,
    service: UnprovisionService = Depends(get_unprovision_service)
) -> UnprovisionStatus:
    """
    Get the status of an unprovisioning operation.

    Returns current unprovisioning status derived from Ironic's provision_state.

    Args:
        operation_id: The operation ID returned from unprovision_server
        service: Unprovision service dependency

    Returns:
        UnprovisionStatus with current unprovisioning status and progress

    Raises:
        HTTPException: 404 if operation not found, 502 if Ironic unreachable
    """
    return await service.get_unprovision_status(operation_id)

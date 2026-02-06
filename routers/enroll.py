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

from dependencies import get_enroll_service
from schemas.enroll import EnrollRequest, EnrollResponse
from services.enroll import EnrollService

router = APIRouter(prefix="/servers", tags=["servers"])


@router.post("", response_model=EnrollResponse, status_code=201)
async def enroll_server(
    request: EnrollRequest,
    service: EnrollService = Depends(get_enroll_service)
) -> EnrollResponse:
    """
    Enroll a new physical server into management.

    Registers the server's BMC credentials and creates an Ironic node.
    Returns 201 Created with the new server details.

    Args:
        request: Enrollment request containing server details
        service: Enrollment service dependency

    Returns:
        EnrollResponse with enrolled server details

    Raises:
        HTTPException: 409 if server name already exists
        HTTPException: 400 if driver type is invalid
        HTTPException: 422 if BMC validation fails
        HTTPException: 502 if Ironic API communication fails
    """
    return await service.enroll_server(request)


@router.get("/{server_id}/enrollment-status", response_model=EnrollResponse)
async def get_enrollment_status(
    server_id: str,
    service: EnrollService = Depends(get_enroll_service)
) -> EnrollResponse:
    """
    Get current enrollment status of a server.

    Returns the server's current state from Ironic. Can be used to poll
    for completion of state transitions initiated during enrollment.

    This endpoint queries Ironic directly - no local state is maintained.
    Safe to call repeatedly for polling.

    Args:
        server_id: UUID of the enrolled server

    Returns:
        EnrollResponse with current server status from Ironic

    Raises:
        HTTPException: 404 if server not found in Ironic
        HTTPException: 502 if Ironic API communication fails
    """
    return await service.get_enrollment_status(server_id)

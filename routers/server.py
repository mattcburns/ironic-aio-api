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

from fastapi import APIRouter, Depends, Query

from dependencies import get_server_service
from schemas.server import ServerListResponse, ServerSummary
from services.server import ServerService

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("", response_model=ServerListResponse)
async def list_servers(
    provision_state: Optional[str] = Query(None, description="Filter by provisioning state"),
    resource_class: Optional[str] = Query(None, description="Filter by resource class"),
    available_only: bool = Query(False, description="Only show servers available for provisioning"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of servers per page"),
    service: ServerService = Depends(get_server_service)
) -> ServerListResponse:
    """
    List all servers with optional filtering and pagination.

    Returns a paginated list of servers managed by Ironic, with options to filter by
    provisioning state, resource class, or availability.

    Args:
        provision_state: Filter by provisioning state (e.g., 'available', 'active')
        resource_class: Filter by resource class (e.g., 'baremetal')
        available_only: Only return servers available for provisioning
        page: Page number (1-indexed)
        page_size: Number of results per page (max 100)
        service: Server service dependency

    Returns:
        ServerListResponse with paginated list of servers

    Raises:
        HTTPException: 502 if Ironic API communication fails
    """
    return await service.list_servers(
        provision_state=provision_state,
        resource_class=resource_class,
        available_only=available_only,
        page=page,
        page_size=page_size
    )


@router.get("/{server_id}", response_model=ServerSummary)
async def get_server(
    server_id: str,
    service: ServerService = Depends(get_server_service)
) -> ServerSummary:
    """
    Get a specific server by ID or name.

    Retrieves detailed information about a single server managed by Ironic.

    Args:
        server_id: The server UUID or name
        service: Server service dependency

    Returns:
        ServerSummary with detailed server information

    Raises:
        HTTPException: 404 if server not found
        HTTPException: 502 if Ironic API communication fails
    """
    return await service.get_server(server_id)

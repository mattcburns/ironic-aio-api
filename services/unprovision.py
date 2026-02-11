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

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from clients.ironic import IronicClient
from schemas.unprovision import UnprovisionRequest, UnprovisionResponse, UnprovisionStatus
from services.server import ServerService


class UnprovisionService:
    """Server unprovisioning business logic."""

    def __init__(self, ironic_client: IronicClient, server_service: ServerService):
        """Initialize unprovisioning service.

        Args:
            ironic_client: Client for interacting with Ironic API
            server_service: Server management service for validation
        """
        self.ironic = ironic_client
        self.server_service = server_service

    async def unprovision_server(
        self,
        request: UnprovisionRequest
    ) -> UnprovisionResponse:
        """
        Initiate server unprovisioning.

        1. Validate server exists and is provisioned
        2. Trigger delete/clean via Ironic API
        3. Return operation tracking ID

        Args:
            request: Unprovisioning request with server ID

        Returns:
            UnprovisionResponse with operation tracking ID

        Raises:
            HTTPException: If unprovisioning fails
        """
        # Get server details
        server = await self._get_server_by_id(request.server_id)

        # Validate server can be unprovisioned
        await self._validate_server_provisionable(server.id, server.provision_state)

        # Trigger unprovisioning in Ironic
        target_state = "deleted" if request.clean else "available"
        try:
            await self.ironic.set_node_provision_state(
                node_id=server.id,
                target_state=target_state
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail="Failed to communicate with Ironic"
            ) from e

        now = datetime.now(timezone.utc)

        return UnprovisionResponse(
            server_id=server.id,
            server_name=server.name,
            status="accepted",
            message=f"Unprovisioning of {server.name} initiated",
            started_at=now
        )

    async def get_unprovision_status(
        self,
        server_id: str
    ) -> UnprovisionStatus:
        """
        Get current status of an unprovisioning operation.

        Status is derived from Ironic's current provision_state:
        - cleaning → in_progress
        - deleting → in_progress
        - available → completed
        - clean failed → failed

        Args:
            server_id: The server ID (Ironic node UUID)

        Returns:
            UnprovisionStatus with current status information

        Raises:
            HTTPException: If operation not found
        """
        # Query Ironic for current provision_state
        try:
            node = await self.ironic.get_node(server_id, ignore_missing=True)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail="Failed to communicate with Ironic"
            ) from e

        if node is None:
            raise HTTPException(
                status_code=404,
                detail=f"Server '{server_id}' not found"
            )

        provision_state = node.provision_state
        now = datetime.now(timezone.utc)

        # Map Ironic provision_state to status
        status_map = {
            "cleaning": "in_progress",
            "deleting": "in_progress",
            "available": "completed",
            "clean failed": "failed",
            "error": "failed",
        }

        status = status_map.get(provision_state, "in_progress")
        progress_map = {
            "cleaning": 50,
            "deleting": 75,
            "available": 100,
            "clean failed": None,
            "error": None,
        }
        progress = progress_map.get(provision_state, None)

        # Set completed_at when operation is finished
        completed_at = None
        if status in ("completed", "failed"):
            # Use node's updated_at if available, else current time
            completed_at = getattr(node, "updated_at", None) or now

        return UnprovisionStatus(
            server_id=node.id,
            status=status,
            provision_state=provision_state,
            progress_percent=progress,
            message=f"Unprovisioning status: {provision_state}",
            started_at=getattr(node, "created_at", None) or now,
            completed_at=completed_at
        )

    async def _get_server_by_id(self, server_id: str) -> "ServerSummary":
        """
        Get server details by ID or name.

        Args:
            server_id: Server ID or name to retrieve

        Returns:
            ServerSummary object with server details

        Raises:
            HTTPException: If server not found
        """
        try:
            # Try to get server from server service
            server = await self.server_service.get_server(server_id)
            return server
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail="Failed to communicate with Ironic"
            ) from e

    async def _validate_server_provisionable(
        self,
        server_id: str,
        provision_state: str
    ) -> None:
        """
        Validate server is in a state that can be unprovisioned.

        Args:
            server_id: Server ID
            provision_state: Current provision state

        Raises:
            HTTPException: If server is not in a provisionable state
        """
        # Server should be in 'active' state to be unprovisioned
        # or in a failed state that needs cleanup
        unprovisionable_states = ["active", "deploy failed", "error"]

        if provision_state not in unprovisionable_states:
            raise HTTPException(
                status_code=409,
                detail=f"Server {server_id} is not in a provisionable state (current: {provision_state})"
            )

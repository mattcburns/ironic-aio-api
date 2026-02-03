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
from schemas.provision import ProvisionRequest, ProvisionResponse, ProvisionStatus
from services.server import ServerService


class ProvisionService:
    """Server provisioning business logic."""

    def __init__(self, ironic_client: IronicClient, server_service: ServerService):
        """Initialize provisioning service.

        Args:
            ironic_client: Client for interacting with Ironic API
            server_service: Server management service for validation
        """
        self.ironic = ironic_client
        self.server_service = server_service

    async def provision_server(
        self,
        request: ProvisionRequest
    ) -> ProvisionResponse:
        """
        Initiate server provisioning.

        1. Select server (specific or auto-select available)
        2. Validate server is in correct state
        3. Set deploy parameters (image, config)
        4. Trigger provisioning via Ironic API
        5. Return operation tracking ID

        Args:
            request: Provisioning request with server details and image

        Returns:
            ProvisionResponse with operation tracking ID

        Raises:
            HTTPException: If provisioning fails
        """
        # Select server
        server_id = await self._select_server(request)

        # Get server details
        server = await self._get_server_by_id(server_id)

        # TODO: Set deploy parameters in Ironic
        # await self.ironic.set_deploy_target(
        #     node_id=server_id,
        #     image_id=request.image_id,
        #     config_drive=request.config_drive
        # )

        # TODO: Trigger provisioning state machine
        # await self.ironic.set_provision_state(
        #     node_id=server_id,
        #     target="active"
        # )

        now = datetime.now(timezone.utc)

        return ProvisionResponse(
            operation_id=server_id,
            server_id=server_id,
            server_name=server.name,
            status="accepted",
            message=f"Provisioning of {server.name} initiated",
            started_at=now
        )

    async def get_provision_status(
        self,
        operation_id: str
    ) -> ProvisionStatus:
        """
        Get current status of a provisioning operation.

        Status is derived from Ironic's current provision_state:
        - deploying → in_progress
        - active → completed
        - deploy failed → failed

        Args:
            operation_id: The operation ID (Ironic node UUID)

        Returns:
            ProvisionStatus with current status information

        Raises:
            HTTPException: If operation not found
        """
        # TODO: Query Ironic for current provision_state
        # ironic_node = await self.ironic.get_node(node_id=operation_id)
        # provision_state = ironic_node.provision_state

        # For now, return mock response
        now = datetime.now(timezone.utc)
        mock_server_id = operation_id
        mock_provision_state = "deploying"

        # Map Ironic provision_state to status
        status_map = {
            "deploying": "in_progress",
            "active": "completed",
            "deploy failed": "failed",
            "manageable": "in_progress",
            "available": "in_progress",
        }

        status = status_map.get(mock_provision_state, "in_progress")
        progress_map = {
            "deploying": 50,
            "active": 100,
            "deploy failed": None,
            "manageable": 25,
            "available": 10,
        }
        progress = progress_map.get(mock_provision_state, None)

        return ProvisionStatus(
            operation_id=operation_id,
            server_id=mock_server_id,
            status=status,
            provision_state=mock_provision_state,
            progress_percent=progress,
            message=f"Provisioning in progress: {mock_provision_state}",
            started_at=now,
            completed_at=None if status != "completed" else now
        )

    async def _select_server(self, request: ProvisionRequest) -> str:
        """
        Select a server for provisioning.

        Args:
            request: Provisioning request with selection criteria

        Returns:
            Selected server ID

        Raises:
            HTTPException: If no suitable server found
        """
        if request.server_id:
            return await self._validate_server_available(request.server_id)
        return await self._auto_select_server(request.resource_class)

    async def _validate_server_available(self, server_id: str) -> str:
        """
        Validate server exists and is available for provisioning.

        Args:
            server_id: Server ID to validate

        Returns:
            Server ID if valid

        Raises:
            HTTPException: If server not found or not available
        """
        await self._get_server_by_id(server_id)
        return server_id

    async def _get_server_by_id(self, server_id: str) -> "ServerSummary":
        """
        Get server details by ID.

        Args:
            server_id: Server ID to retrieve

        Returns:
            ServerSummary object with server details

        Raises:
            HTTPException: If server not found or not available
        """
        try:
            servers = await self.server_service.list_servers(
                available_only=True,
                page_size=100
            )
            for server in servers.servers:
                if server.id == server_id:
                    return server
            raise HTTPException(
                status_code=404,
                detail=f"Server {server_id} not found or not available for provisioning"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail="Failed to communicate with Ironic"
            ) from e

    async def _auto_select_server(
        self,
        resource_class: Optional[str] = None
    ) -> str:
        """
        Auto-select an available server matching criteria.

        Args:
            resource_class: Optional resource class to filter by

        Returns:
            Selected server ID

        Raises:
            HTTPException: If no suitable server found
        """
        try:
            servers = await self.server_service.list_servers(
                available_only=True,
                resource_class=resource_class,
                page_size=100
            )
            if not servers.servers:
                raise HTTPException(
                    status_code=404,
                    detail="No available servers matching criteria"
                )
            # Return first available server
            return servers.servers[0].id
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail="Failed to communicate with Ironic"
            ) from e

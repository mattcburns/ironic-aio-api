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

from fastapi import HTTPException

from clients.ironic import IronicClient
from schemas.enroll import BMCCredentials, EnrollRequest, EnrollResponse


class EnrollService:
    """Server enrollment business logic."""

    def __init__(self, ironic_client: IronicClient):
        """Initialize enrollment service.

        Args:
            ironic_client: Client for interacting with Ironic API
        """
        self.ironic = ironic_client

    async def enroll_server(self, request: EnrollRequest) -> EnrollResponse:
        """
        Enroll a new server into Ironic.

        1. Validate name is unique
        2. Build driver_info from BMC credentials
        3. Create node in Ironic
        4. Optionally validate BMC connectivity
        5. Return enrollment result

        Args:
            request: Enrollment request with server details

        Returns:
            EnrollResponse with enrollment result

        Raises:
            HTTPException: If enrollment fails
        """
        # Validate name is unique
        await self._validate_name_unique(request.name)

        # Build Redfish driver_info from BMC credentials
        driver_info = self._build_redfish_driver_info(request.bmc)

        # TODO: Create node in Ironic
        # node = await self.ironic.create_node(
        #     name=request.name,
        #     driver="redfish",
        #     driver_info=driver_info,
        #     resource_class=request.resource_class,
        #     properties=request.properties or {}
        # )

        # Mock response for now
        server_id = "mock-uuid-12345"
        provision_state = "enroll"

        # Optionally validate BMC connectivity
        if request.validate_bmc:
            bmc_valid = await self._validate_bmc_connectivity(server_id)
            if not bmc_valid:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unable to connect to BMC at {request.bmc.address}"
                )

        return EnrollResponse(
            server_id=server_id,
            server_name=request.name,
            status="enrolled",
            provision_state=provision_state,
            message=f"Server '{request.name}' successfully enrolled",
            created_at=datetime.now(timezone.utc)
        )

    async def _validate_name_unique(self, name: str) -> None:
        """Ensure server name doesn't already exist.

        Args:
            name: Server name to check

        Raises:
            HTTPException: If name already exists
        """
        # TODO: Check if node with this name exists in Ironic
        # existing = await self.ironic.get_node_by_name(name)
        # if existing:
        #     raise HTTPException(
        #         status_code=409,
        #         detail=f"Server with name '{name}' already exists"
        #     )
        pass

    def _build_redfish_driver_info(self, bmc: BMCCredentials) -> dict:
        """Build Redfish driver info.

        Args:
            bmc: BMC credentials

        Returns:
            Redfish-formatted driver_info dictionary
        """
        return {
            "redfish_address": f"https://{bmc.address}",
            "redfish_username": bmc.username,
            "redfish_password": bmc.password,
            "redfish_system_id": "/redfish/v1/Systems/1",
        }

    async def _validate_bmc_connectivity(self, server_id: str) -> bool:
        """Validate BMC is reachable by attempting driver validation.

        Args:
            server_id: UUID of the server to validate

        Returns:
            True if BMC is reachable, False otherwise
        """
        # TODO: Validate BMC connectivity via Ironic
        # try:
        #     await self.ironic.validate_node(server_id)
        #     return True
        # except Exception:
        #     return False

        # Mock success for now
        return True

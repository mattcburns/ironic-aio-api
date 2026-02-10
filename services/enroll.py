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

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from clients.ironic import IronicClient, IronicClientError
from schemas.enroll import BMCCredentials, EnrollRequest, EnrollResponse

logger = logging.getLogger(__name__)

## Server Enrollment
#
# This module combines several steps of server enrollment and management in Ironic
# into a single process.
#
# Enrollment Steps:
# 1. Enroll the node with BMC credentials
# 2. Add the node primary network port based on MAC address
# 3. Configure network settings (IP, netmask, gateway) for cleaning and provisioning
# 4. Mark the node as manageable
# 5. Transition node to available state


class EnrollmentError(HTTPException):
    """Base exception for enrollment errors."""
    pass


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

        Manage transition is synchronous (required before available).
        Provide transition is asynchronous (initiated but not awaited).
        Returns immediately with the current state. Use get_enrollment_status() to poll for completion.

        Steps:
        1. Validate name is unique
        2. Build driver_info from BMC credentials
        3. Create node in Ironic
        4. Add network port with MAC address
        5. Configure network settings (IP, netmask, gateway) for cleaning operations
        6. Transition to manageable state (synchronous, blocks until completion)
        7. Initiate transition to available state (asynchronous, doesn't block)
        8. Optionally validate BMC connectivity
        9. Return enrollment result with current state

        Args:
            request: Enrollment request with server details

        Returns:
            EnrollResponse with enrollment result

        Raises:
            HTTPException: 409 if name already exists
            HTTPException: 502 if Ironic API communication fails or manage transition fails
            HTTPException: 422 if BMC validation fails
        """
        try:
            # Step 1: Validate name is unique
            logger.info(f"Starting enrollment for server: {request.name}")
            await self._validate_name_unique(request.name)
            logger.info(f"Server name validation passed for: {request.name}")

            # Step 2: Build Redfish driver_info from BMC credentials
            driver_info = self._build_redfish_driver_info(
                request.bmc,
                request.redfish_system_id,
                request.redfish_verify_ca,
            )
            logger.debug("Redfish driver_info built successfully")

            # Step 3: Create node in Ironic
            logger.info(f"Creating node in Ironic for: {request.name}")
            node = await self.ironic.create_node(
                name=request.name,
                driver="redfish",
                driver_info=driver_info,
                resource_class=request.resource_class,
                properties=request.properties or {}
            )
            server_id = node.id
            logger.info(f"Node created with ID: {server_id}")

            # Step 4: Add network port with MAC address
            logger.info(f"Adding network port for MAC: {request.network.mac_address}")
            port_extra = {
                "nic_name": request.network.nic_name,
                "ip_address": request.network.ip_address,
                "netmask": request.network.netmask,
                "gateway": request.network.gateway,
            }
            await self.ironic.add_node_port(
                node_id=server_id,
                mac_address=request.network.mac_address,
                extra=port_extra
            )
            logger.info(f"Network port added for: {request.name}")

            # Step 5: Handle state transition to manageable
            # Manage transition is synchronous (required before available)
            logger.info(f"Transitioning node to manageable state for: {request.name}")
            try:
                node = await self.ironic.set_node_provision_state(server_id, "manage")
                provision_state = node.provision_state
                logger.info(f"Node transitioned to state: {provision_state}")
            except IronicClientError as e:
                logger.exception(f"Failed to transition node to manage: {str(e)}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to transition node to manage state: {str(e)}"
                )

            # Get current state from Ironic and return immediately
            current_node = await self.ironic.get_node(server_id)
            provision_state = current_node.provision_state


            # Step 6: Optionally validate BMC connectivity
            if request.validate_bmc:
                logger.info(f"Validating BMC connectivity for: {request.name}")
                bmc_valid = await self._validate_bmc_connectivity(server_id)
                if not bmc_valid:
                    logger.error(f"BMC validation failed for: {request.bmc.address}")
                    raise HTTPException(
                        status_code=422,
                        detail=f"Unable to connect to BMC at {request.bmc.address}"
                    )
                logger.info(f"BMC validation successful for: {request.name}")

            # Step 7: Return enrollment result
            logger.info(f"Enrollment completed successfully for: {request.name}")
            return EnrollResponse(
                server_id=server_id,
                server_name=request.name,
                status="enrolled",
                provision_state=provision_state,
                message=f"Server '{request.name}' enrollment initiated. "
                        f"Current state: {provision_state}. "
                        f"Management state transition is in progress. "
                        f"Use GET /servers/{server_id}/enrollment-status to check progress. "
                        f"Call POST /servers/{server_id}/provide when ready to make available for provisioning.",
                created_at=datetime.now(timezone.utc)
            )

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except IronicClientError as e:
            logger.exception(f"Ironic API error during enrollment of {request.name}")
            raise HTTPException(
                status_code=502,
                detail=f"Ironic API error: {str(e)}"
            )
        except NotImplementedError as e:
            # Handle unimplemented Ironic API calls
            logger.exception(f"Unimplemented Ironic API call during enrollment of {request.name}")
            raise HTTPException(
                status_code=503,
                detail="Required Ironic API functionality not yet implemented"
            )
        except Exception as e:
            logger.exception(f"Unexpected error during enrollment of {request.name}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during enrollment: {str(e)}"
            )

    async def _validate_name_unique(self, name: str) -> None:
        """Ensure server name doesn't already exist.

        Args:
            name: Server name to check

        Raises:
            HTTPException: 409 if name already exists
        """
        try:
            existing = await self.ironic.get_node_by_name(name)
            if existing:
                logger.warning(f"Duplicate server name requested: {name}")
                raise HTTPException(
                    status_code=409,
                    detail=f"Server with name '{name}' already exists"
                )
        except HTTPException:
            raise
        except IronicClientError as e:
            logger.exception(f"Ironic API error during name validation for {name}")
            raise HTTPException(
                status_code=502,
                detail=f"Error validating server name: {str(e)}"
            )
        except NotImplementedError as e:
            # Handle unimplemented API calls
            logger.exception(f"Unimplemented Ironic API call during name validation for {name}")
            raise HTTPException(
                status_code=503,
                detail="Required Ironic API functionality not yet implemented"
            )

    def _build_redfish_driver_info(
        self,
        bmc: BMCCredentials,
        redfish_system_id: str | None = None,
        redfish_verify_ca: bool = False,
    ) -> dict:
        """Build Redfish driver info.

        Args:
            bmc: BMC credentials
            redfish_system_id: Optional Redfish system ID (only included if provided)
            redfish_verify_ca: Whether to verify Redfish CA certificates

        Returns:
            Redfish-formatted driver_info dictionary
        """
        driver_info = {
            "redfish_address": f"https://{bmc.address}",
            "redfish_username": bmc.username,
            "redfish_password": bmc.password,
            "redfish_verify_ca": redfish_verify_ca,
        }

        # Only include redfish_system_id if explicitly provided
        if redfish_system_id is not None:
            driver_info["redfish_system_id"] = redfish_system_id

        # Add optional BMC port if specified
        if bmc.port:
            # Modify the address to include the port
            driver_info["redfish_address"] = f"https://{bmc.address}:{bmc.port}"

        return driver_info

    async def _validate_bmc_connectivity(self, server_id: str) -> bool:
        """Validate BMC is reachable by attempting driver validation.

        Args:
            server_id: UUID of the server to validate

        Returns:
            True if BMC is reachable, False otherwise
        """
        try:
            await self.ironic.validate_node(server_id)
            return True
        except IronicClientError as e:
            logger.warning(f"BMC connectivity validation failed for node {server_id}: {str(e)}")
            return False
        except NotImplementedError:
            # If validation is not implemented, assume it's unavailable for testing
            logger.debug(f"BMC connectivity validation not yet implemented")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during BMC validation for node {server_id}")
            return False

    async def get_enrollment_status(self, server_id: str) -> EnrollResponse:
        """
        Get current enrollment status of a server.

        Queries Ironic for the node's current state. No local state is maintained.
        This is a stateless query that can be called repeatedly to poll for completion.

        Args:
            server_id: UUID of the enrolled server (node ID in Ironic)

        Returns:
            EnrollResponse with current state from Ironic

        Raises:
            HTTPException: 404 if server not found
            HTTPException: 502 if Ironic API communication fails
        """
        try:
            # Query Ironic for current state (no local state)
            node = await self.ironic.get_node(server_id)

            # Map Ironic provision state to human-readable message (pure function)
            message = self._map_provision_state_to_message(node.provision_state)

            return EnrollResponse(
                server_id=node.id,
                server_name=node.name,
                status="enrolled",
                provision_state=node.provision_state,  # Direct from Ironic
                message=message,
                created_at=datetime.now(timezone.utc)  # Response generation time
            )
        except IronicClientError as e:
            logger.exception(f"Ironic API error getting enrollment status for {server_id}")
            raise HTTPException(
                status_code=502,
                detail=f"Ironic API error: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error getting enrollment status for {server_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error getting enrollment status: {str(e)}"
            )

    def _map_provision_state_to_message(self, provision_state: str) -> str:
        """
        Map Ironic provision state to human-readable message.

        Pure function - no state modification.
        """
        state_messages = {
            "available": "Server is ready for provisioning",
            "manageable": "Server is being cleaned before becoming available",
            "manage": "Server is being cleaned before becoming available",
            "enroll": "Server enrolled, waiting to transition to manageable state",
            "cleaning": "Server hardware is being cleaned",
            "clean wait": "Server is waiting for cleaning to complete",
        }
        return state_messages.get(provision_state, f"Server status: {provision_state}")

    async def provide_server(self, server_id: str) -> EnrollResponse:
        """
        Transition a managed server to available state for provisioning.

        Call this after enrollment when the server is ready to join the available pool.
        The node must be in 'manageable' state to proceed.

        Args:
            server_id: UUID or name of the server

        Returns:
            EnrollResponse with updated status

        Raises:
            HTTPException: 404 if server not found
            HTTPException: 400 if server is not in manageable state
            HTTPException: 502 if Ironic API communication fails
        """
        try:
            # Fetch current node to check state
            node = await self.ironic.get_node(server_id, ignore_missing=True)

            if node is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Server '{server_id}' not found"
                )

            current_state = node.provision_state
            if current_state != "manageable":
                raise HTTPException(
                    status_code=400,
                    detail=f"Server must be in 'manageable' state to provide. "
                           f"Current state: {current_state}"
                )

            logger.info(f"Initiating provide transition for server: {server_id}")

            # Initiate transition to provide (asynchronous)
            await self.ironic.set_node_provision_state(server_id, "provide")

            logger.info(f"Provide transition initiated for server: {server_id}")

            # Get current state and return
            current_node = await self.ironic.get_node(server_id)
            provision_state = current_node.provision_state

            return EnrollResponse(
                server_id=server_id,
                server_name=getattr(current_node, "name", "unknown"),
                status="enrolled",
                provision_state=provision_state,
                message=f"Server transition to available initiated. "
                        f"Current state: {provision_state}. "
                        f"Hardware cleaning may take several minutes. "
                        f"Use GET /servers/{server_id}/enrollment-status to check progress.",
                created_at=datetime.now(timezone.utc)
            )

        except HTTPException:
            raise
        except IronicClientError as e:
            logger.exception(f"Ironic API error during provide for {server_id}")
            raise HTTPException(
                status_code=502,
                detail=f"Ironic API error: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error during provide for {server_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during provide: {str(e)}"
            )

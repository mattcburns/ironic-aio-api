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
from dependencies import get_enroll_service
from schemas.enroll import BMCCredentials, EnrollRequest, NetworkInterface


@mcp.tool()
async def enroll_server(
    name: str,
    bmc_address: str,
    bmc_username: str,
    bmc_password: str,
    mac_address: str,
    nic_name: str,
    ip_address: str,
    netmask: str,
    gateway: str,
    resource_class: Optional[str] = None,
    kernel_url: Optional[str] = None,
    ramdisk_url: Optional[str] = None,
    redfish_system_id: Optional[str] = None,
    redfish_verify_ca: bool = False,
) -> dict:
    """
    Enroll a new physical server into Ironic management.

    Args:
        name: Unique name for the server
        bmc_address: BMC IP address or hostname
        bmc_username: BMC username
        bmc_password: BMC password
        mac_address: MAC address of the network interface
        nic_name: Network interface card name (e.g., 'eth0', 'eno1')
        ip_address: IP address for cleaning and provisioning operations
        netmask: Network subnet mask (e.g., '255.255.255.0')
        gateway: Gateway IP address for network routing
        resource_class: Optional resource classification
        kernel_url: Optional deploy kernel URL override
        ramdisk_url: Optional deploy ramdisk URL override
        redfish_system_id: Optional Redfish system ID (defaults to /redfish/v1/Systems/1)
        redfish_verify_ca: Whether to verify Redfish CA certificates

    Returns:
        Enrolled server details including assigned ID
    """
    service = get_enroll_service()
    request = EnrollRequest(
        name=name,
        bmc=BMCCredentials(
            address=bmc_address,
            username=bmc_username,
            password=bmc_password,
        ),
        network=NetworkInterface(
            mac_address=mac_address,
            nic_name=nic_name,
            ip_address=ip_address,
            netmask=netmask,
            gateway=gateway,
        ),
        resource_class=resource_class,
        kernel_url=kernel_url,
        ramdisk_url=ramdisk_url,
        redfish_verify_ca=redfish_verify_ca,
        **({"redfish_system_id": redfish_system_id} if redfish_system_id else {})
    )
    result = await service.enroll_server(request)
    return result.model_dump()


@mcp.tool()
async def get_enrollment_status(server_id: str) -> dict:
    """
    Get current enrollment status of a server.

    Queries Ironic for the node's current state. Use this to poll for completion
    of state transitions initiated during server enrollment. The server is fully
    ready when provision_state becomes 'available'.

    Args:
        server_id: UUID of the enrolled server

    Returns:
        Server enrollment status including current provision state from Ironic
    """
    service = get_enroll_service()
    result = await service.get_enrollment_status(server_id)
    return result.model_dump()


@mcp.tool()
async def provide_server(server_id: str) -> dict:
    """
    Transition a managed server to available state for provisioning.

    Call this after enrollment when the server has completed initial setup
    and is ready to join the available pool.

    Args:
        server_id: UUID or name of the server

    Returns:
        Server status with updated provision state
    """
    service = get_enroll_service()
    result = await service.provide_server(server_id)
    return result.model_dump()

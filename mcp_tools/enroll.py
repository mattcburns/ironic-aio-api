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
    redfish_system_id: Optional[str] = None
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
        redfish_system_id: Optional Redfish system ID (defaults to /redfish/v1/Systems/1)

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
        **({"redfish_system_id": redfish_system_id} if redfish_system_id else {})
    )
    result = await service.enroll_server(request)
    return result.model_dump()

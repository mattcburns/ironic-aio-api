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

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class NetworkInterface(BaseModel):
    """Network interface configuration for server enrollment."""

    mac_address: str = Field(description="MAC address of the network interface")
    nic_name: str = Field(description="Network interface card name (e.g., 'eth0', 'eno1')")
    ip_address: str = Field(description="IP address for cleaning and provisioning operations")
    netmask: str = Field(description="Network subnet mask (e.g., '255.255.255.0' or CIDR notation)")
    gateway: str = Field(description="Gateway IP address for network routing")


class BMCCredentials(BaseModel):
    """BMC connection details."""

    address: str = Field(description="BMC IP address or hostname")
    username: str = Field(description="BMC username")
    password: str = Field(description="BMC password")
    port: Optional[int] = Field(default=None, description="Optional BMC port override")


class EnrollRequest(BaseModel):
    """Request to enroll a new server."""

    name: str = Field(description="Unique server name")
    bmc: BMCCredentials = Field(description="BMC connection details")
    network: NetworkInterface = Field(description="Network interface configuration for cleaning and provisioning")
    resource_class: Optional[str] = Field(default=None, description="Resource classification (e.g., 'baremetal')")
    properties: Optional[dict] = Field(default=None, description="Server properties (CPU, memory, disk info)")
    kernel_url: Optional[str] = Field(
        default=None,
        description="Optional deploy kernel URL (defaults to config value if unset)",
    )
    ramdisk_url: Optional[str] = Field(
        default=None,
        description="Optional deploy ramdisk URL (defaults to config value if unset)",
    )
    redfish_system_id: Optional[str] = Field(default=None, description="Redfish system ID for the BMC (only sent if specified)")
    redfish_verify_ca: bool = Field(
        default=False,
        description="Verify Redfish CA certificate during enrollment",
    )
    validate_bmc: bool = Field(default=True, description="Test BMC connectivity during enrollment")


class EnrollResponse(BaseModel):
    """Enrollment operation result."""

    server_id: str = Field(description="UUID assigned by Ironic")
    server_name: str = Field(description="Name of the enrolled server")
    status: Literal["enrolled", "failed"] = Field(description="Enrollment status")
    provision_state: str = Field(description="Current Ironic provision state")
    message: str = Field(description="Human-readable status message")
    created_at: datetime = Field(description="Enrollment timestamp")

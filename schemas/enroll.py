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


class BMCCredentials(BaseModel):
    """BMC connection details."""

    driver: str = Field(default="ipmi", description="BMC driver type (ipmi, redfish, ilo, idrac)")
    address: str = Field(description="BMC IP address or hostname")
    username: str = Field(description="BMC username")
    password: str = Field(description="BMC password")
    port: Optional[int] = Field(default=None, description="BMC port (defaults vary by driver)")


class EnrollRequest(BaseModel):
    """Request to enroll a new server."""

    name: str = Field(description="Unique server name")
    bmc: BMCCredentials = Field(description="BMC connection details")
    resource_class: Optional[str] = Field(default=None, description="Resource classification (e.g., 'baremetal')")
    properties: Optional[dict] = Field(default=None, description="Server properties (CPU, memory, disk info)")
    validate_bmc: bool = Field(default=True, description="Test BMC connectivity during enrollment")


class EnrollResponse(BaseModel):
    """Enrollment operation result."""

    server_id: str = Field(description="UUID assigned by Ironic")
    server_name: str = Field(description="Name of the enrolled server")
    status: Literal["enrolled", "failed"] = Field(description="Enrollment status")
    provision_state: str = Field(description="Current Ironic provision state")
    message: str = Field(description="Human-readable status message")
    created_at: datetime = Field(description="Enrollment timestamp")

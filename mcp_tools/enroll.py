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
from schemas.enroll import BMCCredentials, EnrollRequest


@mcp.tool()
async def enroll_server(
    name: str,
    bmc_address: str,
    bmc_username: str,
    bmc_password: str,
    driver: str = "ipmi",
    resource_class: Optional[str] = None
) -> dict:
    """
    Enroll a new physical server into Ironic management.

    Args:
        name: Unique name for the server
        bmc_address: BMC IP address or hostname
        bmc_username: BMC username
        bmc_password: BMC password
        driver: BMC driver type (ipmi, redfish, ilo, idrac)
        resource_class: Optional resource classification

    Returns:
        Enrolled server details including assigned ID
    """
    service = get_enroll_service()
    request = EnrollRequest(
        name=name,
        bmc=BMCCredentials(
            driver=driver,
            address=bmc_address,
            username=bmc_username,
            password=bmc_password,
        ),
        resource_class=resource_class,
    )
    result = await service.enroll_server(request)
    return result.model_dump()

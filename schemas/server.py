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
from typing import Optional

from pydantic import BaseModel, Field


class ServerSummary(BaseModel):
    """Business-friendly server representation."""

    id: str = Field(description="Ironic node UUID")
    name: str = Field(description="Server name")
    provision_state: str = Field(description="Current provisioning state")
    power_state: Optional[str] = Field(default=None, description="Current power state")
    resource_class: Optional[str] = Field(default=None, description="Resource classification")
    is_available: bool = Field(description="Whether server is available for provisioning")
    properties: dict = Field(default_factory=dict, description="Server properties (CPU, memory, disk info)")
    created_at: datetime = Field(description="Server creation timestamp")
    updated_at: datetime = Field(description="Server last update timestamp")


class ServerListResponse(BaseModel):
    """Response containing a list of servers with pagination."""

    servers: list[ServerSummary] = Field(description="List of servers")
    total: int = Field(description="Total number of servers")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of servers per page")

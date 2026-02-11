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


class UnprovisionRequest(BaseModel):
    """Request to unprovision a server."""

    server_id: str = Field(
        description="Server ID or name to unprovision"
    )
    clean: bool = Field(
        default=True,
        description="Whether to run cleaning/wiping steps"
    )


class UnprovisionResponse(BaseModel):
    """Unprovisioning operation result."""

    server_id: str = Field(
        description="Server UUID (Ironic node UUID)"
    )
    server_name: str = Field(
        description="Server name"
    )
    status: Literal["accepted", "in_progress", "completed", "failed"] = Field(
        description="Unprovisioning status"
    )
    message: str = Field(
        description="Status message"
    )
    started_at: datetime = Field(
        description="When unprovisioning started"
    )


class UnprovisionStatus(BaseModel):
    """Status of an unprovisioning operation."""

    server_id: str = Field(
        description="Server UUID (Ironic node UUID)"
    )
    status: Literal["in_progress", "completed", "failed"] = Field(
        description="Current unprovisioning status"
    )
    provision_state: str = Field(
        description="Ironic provision_state value"
    )
    progress_percent: Optional[int] = Field(
        default=None,
        description="Estimated progress percentage"
    )
    message: str = Field(
        description="Status message"
    )
    started_at: datetime = Field(
        description="When unprovisioning started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When unprovisioning completed"
    )

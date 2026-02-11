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


class ProvisionRequest(BaseModel):
    """Request to provision a server."""

    server_id: Optional[str] = Field(
        default=None,
        description="Specific server ID to provision, or None for auto-select"
    )
    resource_class: Optional[str] = Field(
        default=None,
        description="Resource class for auto-selection if server_id not provided"
    )
    image_source: str = Field(
        description="Image source URL, Glance image UUID, or image ID"
    )
    image_checksum: Optional[str] = Field(
        default=None,
        description="MD5 or SHA checksum of the image for verification"
    )
    config_drive: Optional[dict] = Field(
        default=None,
        description="Cloud-init user data configuration"
    )


class ProvisionResponse(BaseModel):
    """Provisioning operation result."""
    server_id: str = Field(
        description="Server UUID"
    )
    server_name: str = Field(
        description="Server name"
    )
    status: Literal["accepted", "in_progress", "completed", "failed"] = Field(
        description="Provisioning status"
    )
    message: str = Field(
        description="Status message"
    )
    started_at: datetime = Field(
        description="When provisioning started"
    )


class ProvisionStatus(BaseModel):
    """Status of a provisioning operation."""
    server_id: str = Field(
        description="Server UUID"
    )
    status: Literal["in_progress", "completed", "failed"] = Field(
        description="Current provisioning status"
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
        description="When provisioning started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When provisioning completed"
    )

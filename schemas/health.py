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

"""Health check schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Represents the current health status of the API."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall API health status."
    )
    version: str = Field(..., description="API version.")
    timestamp: datetime = Field(..., description="UTC timestamp of the check.")
    ironic_connected: bool = Field(
        ..., description="Whether the Ironic API is reachable."
    )
    ironic_api_version: Optional[str] = Field(
        None, description="Ironic API microversion when available."
    )

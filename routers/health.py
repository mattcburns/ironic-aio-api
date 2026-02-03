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

"""Health check REST endpoint."""

from fastapi import APIRouter, Depends

from schemas.health import HealthStatus
from services.health import HealthService, get_health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthStatus,
    summary="Health check",
    description="Check the health of the API and its dependencies.",
)
async def get_health(
    service: HealthService = Depends(get_health_service),
) -> HealthStatus:
    """Return the current health status."""

    return await service.check_health()

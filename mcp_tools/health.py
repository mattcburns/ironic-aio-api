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

"""Health check MCP tool."""

from app import mcp
from services.health import get_health_service


@mcp.tool()
async def check_health() -> dict:
    """Check the health of the ironic-aio API."""

    service = get_health_service()
    result = await service.check_health()
    return result.model_dump()

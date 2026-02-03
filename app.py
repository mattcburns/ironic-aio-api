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

"""FastAPI application entry point."""

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from config import get_settings
from routers.health import router as health_router
from routers.enroll import router as enroll_router
from routers.server import router as server_router
from routers.provision import router as provision_router

settings = get_settings()

app = FastAPI(
	title="Ironic AIO API",
	description="Business process API for OpenStack Ironic operations",
	version=settings.app_version,
)

app.include_router(health_router)
app.include_router(enroll_router)
app.include_router(server_router)
app.include_router(provision_router)

mcp = FastMCP("ironic-aio")

# Register MCP tools (side-effect import)
from mcp_tools import health as _health  # noqa: F401
from mcp_tools import enroll as _enroll  # noqa: F401
from mcp_tools import server as _server  # noqa: F401
from mcp_tools import provision as _provision  # noqa: F401

app.mount("/mcp", mcp.sse_app())

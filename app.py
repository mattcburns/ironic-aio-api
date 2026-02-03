"""FastAPI application entry point."""

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from config import get_settings
from routers.health import router as health_router

settings = get_settings()

app = FastAPI(
	title="Ironic AIO API",
	description="Business process API for OpenStack Ironic operations",
	version=settings.app_version,
)

app.include_router(health_router)

mcp = FastMCP("ironic-aio")

# Register MCP tools (side-effect import)
from mcp_tools import health as _health  # noqa: F401

app.mount("/mcp", mcp.sse_app())

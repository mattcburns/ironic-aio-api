"""Health check MCP tool."""

from app import mcp
from services.health import get_health_service


@mcp.tool()
async def check_health() -> dict:
    """Check the health of the ironic-aio API."""

    service = get_health_service()
    result = await service.check_health()
    return result.model_dump()

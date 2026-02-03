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

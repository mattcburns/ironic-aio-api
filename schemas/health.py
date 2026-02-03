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

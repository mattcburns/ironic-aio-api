"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based configuration for the API."""

    app_name: str = "ironic-aio-api"
    app_version: str = "0.1.0"
    debug: bool = False
    ironic_api_url: str = "http://localhost:6385"
    ironic_api_version: str = "1.82"

    model_config = SettingsConfigDict(env_prefix="IRONIC_AIO_")


def get_settings() -> Settings:
    """Create settings from environment variables."""

    return Settings()

"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based configuration for the API."""

    app_name: str = "ironic-aio-api"
    app_version: str = "0.1.0"
    debug: bool = False
    ironic_api_url: str = "http://localhost:6385"
    ironic_api_version: str = "1.82"
    ironic_basic_auth_username: str | None = None
    ironic_basic_auth_password: str | None = None
    ironic_skip_ca_verification: bool = False
    kernel_url: str | None = None
    ramdisk_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="IRONIC_AIO_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


def get_settings() -> Settings:
    """Create settings from environment variables."""

    return Settings()

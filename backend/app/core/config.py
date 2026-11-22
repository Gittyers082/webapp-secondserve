"""App settings, read from environment variables (or backend/.env in development)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    cors_origins: str = "http://localhost:4321"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/secondserve"

    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "listing-images"
    jwt_audience: str = "authenticated"

    redis_url: str = ""

    resend_api_key: str = ""
    email_from: str = "SecondServe <onboarding@resend.dev>"
    celery_enabled: bool = False

    commission_rate: float = Field(default=0.07, ge=0, le=0.5)
    # Unsold listings this close to expiry move to the partner Surplus Board (FR-SYS-14).
    surplus_window_hours: int = Field(default=6, ge=1, le=48)
    # FR-BUS-3 / NFR-BUS-MV-1: discounts should land in this range.
    min_discount_percent: int = 15
    max_discount_percent: int = 90

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()

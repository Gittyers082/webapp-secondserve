"""Alembic migration runner (async, reads DATABASE_URL from settings)."""

import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # Supabase owns the auth/storage schemas; only manage our own tables in "public".
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(
        get_settings().database_url, connect_args={"statement_cache_size": 0}
    )
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
# Copy this file to backend/.env and fill in the values.
# NEVER commit .env. Ask the project lead for the real values.

ENVIRONMENT=development

# Comma-separated list of frontend origins allowed to call the API.
CORS_ORIGINS=http://localhost:4321

# --- Database (Supabase Postgres) ---
# Supabase dashboard > Connect > "Session pooler" connection string.
# Change the scheme to postgresql+asyncpg://
DATABASE_URL=postgresql+asyncpg://postgres.glcwsiulaqiympfesdwa:secondSERVEXx2026@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres

# --- Supabase Auth ---
SUPABASE_URL=https://glcwsiulaqiympfesdwa.supabase.co
# Leave empty if the project uses the new JWT signing keys (JWKS is used automatically).
# Fill in only if the project still uses the legacy shared JWT secret.
SUPABASE_JWT_SECRET=
# Server-side key, used only for Storage uploads. Keep secret.
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdsY3dzaXVsYXFpeW1wZmVzZHdhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5NTM0MzAwOSwiZXhwIjoyMTEwOTE5MDA5fQ.rp2Xq2eWyVfbxdOnH5YRZagF1c0prSLbbjw5_E640wM
SUPABASE_STORAGE_BUCKET=listing-images

# --- Redis (Upstash) ---
# Upstash dashboard > your database > "Redis" connection string (rediss://...)
REDIS_URL=

# --- Email (Resend) ---
RESEND_API_KEY=
EMAIL_FROM=SecondServe <onboarding@resend.dev>

# Set to true once a Celery worker is running; otherwise emails are skipped
# (in-app notifications are still saved).
CELERY_ENABLED=false

# --- Business rules ---
COMMISSION_RATE=0.07
# Hours before expiry when unsold listings move to the partner Surplus Board.
SURPLUS_WINDOW_HOURS=6
"""Finishing sign-up (POST /api/me/profile) against a real Postgres.

Skipped unless TEST_DATABASE_URL is set. Use a throwaway database, never Supabase:
the tables are dropped and recreated for every test.
"""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.deps import get_token_claims
from app.core.security import TokenClaims
from app.db.session import get_db
from app.main import app
from app.models import AccountStatus, AuditLog, Base, User

TEST_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
async def sessions():
    engine = create_async_engine(TEST_URL, connect_args={"statement_cache_size": 0})
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def sign_up(maker, body: dict) -> tuple[uuid.UUID, int, dict]:
    """POST /api/me/profile as a freshly signed-in Supabase user."""
    user_id = uuid.uuid4()

    async def db_override():
        async with maker() as db:
            yield db

    async def claims():
        return TokenClaims(user_id=user_id, email=f"{body['username']}@example.com")

    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_token_claims] = claims
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/api/me/profile", json=body)
    finally:
        app.dependency_overrides.clear()
    return user_id, response.status_code, response.json()


async def test_buyer_sign_up_creates_the_user_and_its_audit_row(sessions):
    user_id, code, body = await sign_up(
        sessions, {"role": "buyer", "username": "ana", "fullName": "Ana Cruz"}
    )
    assert code == 201, body
    assert body["role"] == "buyer" and body["status"] == "active"
    async with sessions() as db:
        assert (await db.get(User, user_id)) is not None
        audit = await db.scalar(select(AuditLog).where(AuditLog.actor_id == user_id))
        assert audit.action == "user.register"


async def test_seller_and_partner_sign_up_wait_for_approval(sessions):
    _, code, seller = await sign_up(
        sessions,
        {
            "role": "seller",
            "username": "sam",
            "fullName": "Sam Reyes",
            "seller": {
                "businessName": "Sam Bakery",
                "businessType": "bakery",
                "businessAddress": "Session Rd, Baguio",
                "contactPhone": "09171234567",
            },
        },
    )
    assert code == 201, seller
    assert seller["status"] == AccountStatus.pending.value

    _, code, partner = await sign_up(
        sessions,
        {
            "role": "partner",
            "username": "pat",
            "fullName": "Pat Lim",
            "partner": {
                "organizationName": "Aurora Hill Pantry",
                "organizationType": "charity",
                "contactPerson": "Pat Lim",
                "address": "Aurora Hill, Baguio",
            },
        },
    )
    assert code == 201, partner
    assert partner["status"] == AccountStatus.pending.value

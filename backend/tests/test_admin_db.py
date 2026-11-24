"""Admin moderation, sessions and stats against a real Postgres.

Skipped unless TEST_DATABASE_URL is set. Use a throwaway database, never Supabase:
the tables are dropped and recreated for every test.
"""

import contextlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.models import (
    AccountStatus,
    Base,
    FoodCategory,
    Listing,
    ListingStatus,
    Notification,
    Role,
    SellerProfile,
    User,
)
from app.schemas.order import OrderCreate
from app.services import orders as svc

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


async def make_user(maker, name: str, role: Role, **overrides) -> User:
    async with maker() as db:
        user = User(
            id=uuid.uuid4(),
            email=f"{name}@example.com",
            username=name,
            full_name=name.title(),
            role=role,
            **overrides,
        )
        db.add(user)
        if role == Role.seller:
            db.add(
                SellerProfile(
                    user_id=user.id,
                    business_name=f"{name.title()} Bakery",
                    business_type="bakery",
                    business_address="Session Rd",
                    contact_phone="0917",
                )
            )
        await db.commit()
        return user


async def make_listing(maker, seller: User, name="Pandesal", quantity=5) -> Listing:
    async with maker() as db:
        listing = Listing(
            seller_id=seller.id,
            name=name,
            description="Fresh this morning",
            category=FoodCategory.bread,
            original_price=Decimal("100"),
            discounted_price=Decimal("50"),
            quantity_available=quantity,
            original_quantity=quantity,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
            pickup_location="Session Rd",
        )
        db.add(listing)
        await db.commit()
        return listing


@contextlib.asynccontextmanager
async def api(maker, user: User | None = None):
    async def db_override():
        async with maker() as db:
            yield db

    async def me():
        async with maker() as db:
            return await db.get(User, user.id)

    app.dependency_overrides[get_db] = db_override
    if user is not None:
        app.dependency_overrides[get_current_user] = me
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def test_admin_flags_and_removes_a_listing(sessions):
    admin = await make_user(sessions, "ana", Role.admin)
    seller = await make_user(sessions, "sam", Role.seller)
    fine = await make_listing(sessions, seller, "Pandesal")
    shady = await make_listing(sessions, seller, "Mystery tray")

    async with api(sessions, seller) as client:  # sellers can't moderate
        assert (await client.get("/api/admin/listings")).status_code == 403

    async with api(sessions, admin) as client:
        flagged = await client.post(
            f"/api/admin/listings/{shady.id}/flag", json={"reason": "No expiry photo"}
        )
        assert flagged.status_code == 200
        assert flagged.json()["flagged"] and flagged.json()["flagReason"] == "No expiry photo"

        listed = (await client.get("/api/admin/listings")).json()
        assert listed[0]["name"] == "Mystery tray"  # flagged first
        only = (await client.get("/api/admin/listings", params={"flagged": "true"})).json()
        assert [i["name"] for i in only] == ["Mystery tray"]

        cleared = (await client.post(f"/api/admin/listings/{fine.id}/unflag")).json()
        assert cleared["flagged"] is False

        removed = await client.delete(f"/api/admin/listings/{shady.id}")
        assert removed.status_code == 204
        again = await client.delete(f"/api/admin/listings/{shady.id}")
        assert again.status_code == 204  # removing twice is harmless

    async with sessions() as db:
        assert (await db.get(Listing, shady.id)).status == ListingStatus.removed

    async with api(sessions) as client:  # gone from the Shop
        names = [i["name"] for i in (await client.get("/api/listings")).json()["items"]]
        assert names == ["Pandesal"]


async def test_active_sessions_show_recent_users_only(sessions):
    now = datetime.now(timezone.utc)
    admin = await make_user(sessions, "ana", Role.admin, last_seen_at=now)
    await make_user(sessions, "ben", Role.buyer, last_seen_at=now - timedelta(minutes=5))
    await make_user(sessions, "old", Role.buyer, last_seen_at=now - timedelta(hours=2))
    await make_user(sessions, "bad", Role.buyer, last_seen_at=now, status=AccountStatus.banned)
    await make_user(sessions, "new", Role.buyer)  # never signed in

    async with api(sessions, admin) as client:
        online = (await client.get("/api/admin/sessions")).json()
    assert [s["username"] for s in online] == ["ana", "ben"]


async def test_stats_count_rescued_food(sessions):
    admin = await make_user(sessions, "ana", Role.admin)
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ben", Role.buyer)
    await make_user(sessions, "pen", Role.seller, status=AccountStatus.pending)
    listing = await make_listing(sessions, seller, quantity=5)

    async with sessions() as db:
        order, _ = await svc.place_order(db, buyer, OrderCreate(listing_id=listing.id, quantity=2))
    async with sessions() as db:
        await svc.mark_picked_up(db, seller, order.id, order.pickup_code)

    async with api(sessions, admin) as client:
        numbers = (await client.get("/api/admin/stats")).json()
    assert numbers["usersByRole"] == {"admin": 1, "seller": 2, "buyer": 1}
    assert numbers["pendingAccounts"] == 1
    assert numbers["activeListings"] == 1
    assert numbers["ordersByStatus"] == {"picked-up": 1}
    assert numbers["itemsRescued"] == 2
    assert Decimal(numbers["revenue"]) == 100 and Decimal(numbers["commission"]) == Decimal("7")
    assert Decimal(numbers["customerSavings"]) == 100
    assert numbers["averageDiscountPercent"] == 50


async def test_approval_message_fits_the_role(sessions):
    admin = await make_user(sessions, "ana", Role.admin)
    partner = await make_user(sessions, "pat", Role.partner, status=AccountStatus.pending)

    async with api(sessions, admin) as client:
        decided = await client.post(
            f"/api/admin/approvals/{partner.id}", json={"decision": "approved"}
        )
    assert decided.status_code == 200 and decided.json()["status"] == "active"

    async with sessions() as db:
        note = await db.scalar(select(Notification).where(Notification.user_id == partner.id))
    assert "Surplus Board" in note.body

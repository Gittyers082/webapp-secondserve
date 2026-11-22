"""Order and search tests against a real Postgres (row locking can't be tested without one).

Skipped unless TEST_DATABASE_URL is set, for example:
    TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/secondserve_test pytest
Use a throwaway database: the tables are dropped and recreated for every test.
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models import (
    Base,
    FoodCategory,
    Listing,
    ListingStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Role,
    SellerProfile,
    User,
)
from app.schemas.order import CheckoutIn, CheckoutLine, OrderCreate
from app.schemas.review import ReviewCreate
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
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


async def make_user(maker, name: str, role: Role) -> User:
    async with maker() as db:
        user = User(
            id=uuid.uuid4(),
            email=f"{name}@example.com",
            username=name,
            full_name=name.title(),
            role=role,
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


async def make_listing(maker, seller: User, name="Pandesal", quantity=1, **overrides) -> Listing:
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
            **overrides,
        )
        db.add(listing)
        await db.commit()
        return listing


async def reload(maker, listing_id) -> Listing:
    async with maker() as db:
        return await db.get(Listing, listing_id, populate_existing=True)


async def reserve(maker, buyer, listing_id, quantity=1, method=PaymentMethod.pay_on_pickup):
    async with maker() as db:
        return await svc.place_order(
            db, buyer, OrderCreate(listing_id=listing_id, quantity=quantity, payment_method=method)
        )


async def test_two_buyers_cannot_both_get_the_last_item(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    b1 = await make_user(sessions, "ana", Role.buyer)
    b2 = await make_user(sessions, "ben", Role.buyer)
    listing = await make_listing(sessions, seller, quantity=1)

    results = await asyncio.gather(
        reserve(sessions, b1, listing.id),
        reserve(sessions, b2, listing.id),
        return_exceptions=True,
    )

    failures = [r for r in results if isinstance(r, HTTPException)]
    assert len(failures) == 1 and failures[0].status_code == 409
    after = await reload(sessions, listing.id)
    assert after.quantity_available == 0 and after.status == ListingStatus.sold_out


async def test_many_buyers_never_oversell(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    listing = await make_listing(sessions, seller, quantity=5)
    buyers = [await make_user(sessions, f"buyer{i}", Role.buyer) for i in range(12)]

    results = await asyncio.gather(
        *(reserve(sessions, b, listing.id) for b in buyers), return_exceptions=True
    )

    assert sum(not isinstance(r, Exception) for r in results) == 5
    assert (await reload(sessions, listing.id)).quantity_available == 0


async def test_checkout_is_all_or_nothing(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ana", Role.buyer)
    plenty = await make_listing(sessions, seller, "Ensaymada", quantity=5)
    scarce = await make_listing(sessions, seller, "Cake", quantity=1)

    cart = CheckoutIn(
        items=[
            CheckoutLine(listing_id=plenty.id, quantity=2),
            CheckoutLine(listing_id=scarce.id, quantity=3),
        ]
    )
    async with sessions() as db:
        with pytest.raises(HTTPException) as err:
            await svc.checkout(db, buyer, cart)
    assert err.value.status_code == 409
    assert (await reload(sessions, plenty.id)).quantity_available == 5


async def test_opposite_cart_orders_do_not_deadlock(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    a = await make_listing(sessions, seller, "Bread A", quantity=10)
    b = await make_listing(sessions, seller, "Bread B", quantity=10)
    b1 = await make_user(sessions, "ana", Role.buyer)
    b2 = await make_user(sessions, "ben", Role.buyer)

    async def run(buyer, first, second):
        cart = CheckoutIn(
            items=[
                CheckoutLine(listing_id=first.id, quantity=1),
                CheckoutLine(listing_id=second.id, quantity=1),
            ]
        )
        async with sessions() as db:
            return await svc.checkout(db, buyer, cart)

    carts = [run(b1, a, b) if i % 2 else run(b2, b, a) for i in range(10)]
    results = await asyncio.wait_for(asyncio.gather(*carts), timeout=15)
    assert all(len(r) == 2 for r in results)
    assert (await reload(sessions, a.id)).quantity_available == 0


async def test_cancel_puts_stock_back_and_refunds(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ana", Role.buyer)
    listing = await make_listing(sessions, seller, quantity=2)
    order, _ = await reserve(sessions, buyer, listing.id, 2, PaymentMethod.gcash_simulated)
    assert (await reload(sessions, listing.id)).status == ListingStatus.sold_out

    async with sessions() as db:
        cancelled, _ = await svc.cancel_order(db, buyer, order.id)

    assert cancelled.status == OrderStatus.cancelled
    assert cancelled.payment.status == PaymentStatus.refunded
    after = await reload(sessions, listing.id)
    assert after.quantity_available == 2 and after.status == ListingStatus.active


async def test_only_the_buyer_can_cancel(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ana", Role.buyer)
    other = await make_user(sessions, "ben", Role.buyer)
    listing = await make_listing(sessions, seller, quantity=2)
    order, _ = await reserve(sessions, buyer, listing.id)

    async with sessions() as db:
        with pytest.raises(HTTPException) as err:
            await svc.cancel_order(db, other, order.id)
    assert err.value.status_code == 404


async def test_pickup_review_flow(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ana", Role.buyer)
    listing = await make_listing(sessions, seller, quantity=3)
    order, _ = await reserve(sessions, buyer, listing.id)

    async with sessions() as db:  # can't review before pickup
        with pytest.raises(HTTPException) as err:
            await svc.create_review(db, buyer, order.id, ReviewCreate(rating=5))
    assert err.value.status_code == 409

    async with sessions() as db:
        with pytest.raises(HTTPException) as err:
            await svc.mark_picked_up(db, seller, order.id, "WRONG1")
    assert err.value.status_code == 400

    async with sessions() as db:
        ready = await svc.mark_ready(db, seller, order.id)
    assert ready.status == OrderStatus.ready

    async with sessions() as db:  # code match ignores case and spaces
        done = await svc.mark_picked_up(db, seller, order.id, f" {order.pickup_code.lower()} ")
    assert done.status == OrderStatus.picked_up and done.picked_up_at
    assert done.payment.status == PaymentStatus.paid

    async with sessions() as db:
        await svc.create_review(db, buyer, order.id, ReviewCreate(rating=4, comment="Soft"))
    async with sessions() as db:
        with pytest.raises(HTTPException) as err:
            await svc.create_review(db, buyer, order.id, ReviewCreate(rating=5))
    assert err.value.status_code == 409

    async with sessions() as db:  # can't cancel after pickup
        with pytest.raises(HTTPException) as err:
            await svc.cancel_order(db, buyer, order.id)
    assert err.value.status_code == 409


async def test_search_is_typo_tolerant_and_ranked(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    await make_listing(sessions, seller, "Pandesal box")
    await make_listing(sessions, seller, "Chocolate cake")

    async def override():
        async with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            typo = (await client.get("/api/listings", params={"q": "pandsal"})).json()
            assert [i["name"] for i in typo["items"]] == ["Pandesal box"]
            ranked = (
                await client.get("/api/listings", params={"q": "cake", "sort": "relevance"})
            ).json()
            assert ranked["items"][0]["name"] == "Chocolate cake"
            wildcard = (await client.get("/api/listings", params={"q": "%"})).json()
            assert wildcard["total"] == 0  # % is searched literally, not as a wildcard
    finally:
        app.dependency_overrides.clear()

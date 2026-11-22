"""Order and search tests against a real Postgres (row locking can't be tested without one).

Skipped unless TEST_DATABASE_URL is set, for example:
    TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/secondserve_test pytest
Use a throwaway database: the tables are dropped and recreated for every test.
"""

import asyncio
import contextlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.models import (
    Base,
    FoodCategory,
    FulfillmentOption,
    Listing,
    ListingKind,
    ListingStatus,
    OrderStatus,
    PartnerProfile,
    PaymentMethod,
    PaymentStatus,
    PaymentTransaction,
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
        if role == Role.partner:
            db.add(
                PartnerProfile(
                    user_id=user.id,
                    organization_name=f"{name.title()} Food Bank",
                    organization_type="food-bank",
                    address="Harrison Rd",
                    contact_phone="0918",
                )
            )
        await db.commit()
        return user


async def make_listing(maker, seller: User, name="Pandesal", quantity=1, **overrides) -> Listing:
    async with maker() as db:
        fields = dict(
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
        listing = Listing(**{**fields, **overrides})
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


# ---------------------------------------------------------------- partners and delivery


@contextlib.asynccontextmanager
async def api(maker, user: User | None = None):
    """An HTTP client for the real app, logged in as `user` (or not logged in)."""

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


async def test_two_partners_cannot_both_claim_the_last_donation(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    p1 = await make_user(sessions, "pat", Role.partner)
    p2 = await make_user(sessions, "pia", Role.partner)
    donation = await make_listing(
        sessions, seller, quantity=1, kind=ListingKind.donation, discounted_price=Decimal("0")
    )

    results = await asyncio.gather(
        reserve(sessions, p1, donation.id),
        reserve(sessions, p2, donation.id),
        return_exceptions=True,
    )

    failures = [r for r in results if isinstance(r, HTTPException)]
    assert len(failures) == 1 and failures[0].status_code == 409
    winner = next(r for r in results if not isinstance(r, Exception))[0]
    assert winner.total == 0 and winner.payment.status == PaymentStatus.paid  # nothing to pay
    assert (await reload(sessions, donation.id)).status == ListingStatus.sold_out


async def test_buyers_and_partners_stay_on_their_own_side(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ana", Role.buyer)
    partner = await make_user(sessions, "pat", Role.partner)
    retail = await make_listing(sessions, seller, "Retail bread", quantity=3)
    offer = await make_listing(
        sessions, seller, "Offer bread", quantity=3, kind=ListingKind.partner_offer
    )

    with pytest.raises(HTTPException) as err:
        await reserve(sessions, buyer, offer.id)
    assert err.value.status_code == 403
    with pytest.raises(HTTPException) as err:
        await reserve(sessions, partner, retail.id)
    assert err.value.status_code == 403
    order, _ = await reserve(sessions, partner, offer.id, 2)
    assert order.buyer_id == partner.id


async def test_convert_listing_and_surplus_board(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ana", Role.buyer)
    partner = await make_user(sessions, "pat", Role.partner)
    to_offer = await make_listing(sessions, seller, "Offer bread", quantity=5)
    to_gift = await make_listing(sessions, seller, "Gift bread", quantity=5)
    later = await make_listing(
        sessions,
        seller,
        "Next week bread",
        quantity=5,
        kind=ListingKind.partner_offer,
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
    )

    async with api(sessions, seller) as client:
        bad = await client.post(
            f"/api/listings/{to_offer.id}/convert", json={"kind": "partner-offer"}
        )
        assert bad.status_code == 422  # offer needs a price
        pricey = await client.post(
            f"/api/listings/{to_offer.id}/convert",
            json={"kind": "partner-offer", "partnerPrice": 60},
        )
        assert pricey.status_code == 422  # not lower than the current 50
        ok = await client.post(
            f"/api/listings/{to_offer.id}/convert",
            json={"kind": "partner-offer", "partnerPrice": 20},
        )
        assert ok.status_code == 200
        assert ok.json()["kind"] == "partner-offer" and ok.json()["discountPercent"] == 80
        again = await client.post(f"/api/listings/{to_offer.id}/convert", json={"kind": "donation"})
        assert again.status_code == 409
        gift = await client.post(f"/api/listings/{to_gift.id}/convert", json={"kind": "donation"})
        assert gift.status_code == 200 and gift.json()["discountPercent"] == 100

    async with api(sessions) as client:  # the marketplace no longer shows them
        assert (await client.get("/api/listings")).json()["total"] == 0

    async with api(sessions, buyer) as client:
        assert (await client.get("/api/surplus")).status_code == 403

    async with api(sessions, partner) as client:
        board = (await client.get("/api/surplus")).json()
        assert board["total"] == 3
        assert board["items"][0]["name"] != "Next week bread"  # soonest to expire first
        donations = (await client.get("/api/surplus", params={"kind": "donation"})).json()
        assert [i["name"] for i in donations["items"]] == ["Gift bread"]
        soon = (await client.get("/api/surplus", params={"expiringSoon": "true"})).json()
        assert {i["name"] for i in soon["items"]} == {"Offer bread", "Gift bread"}
        cheap = (await client.get("/api/surplus", params={"maxPrice": 0})).json()
        assert [i["name"] for i in cheap["items"]] == ["Gift bread"]
        assert (await client.get("/api/surplus", params={"q": "gift"})).json()["total"] == 1
    assert later.id  # created above, only to check expiringSoon leaves it out


async def test_delivery_flow(sessions):
    seller = await make_user(sessions, "sam", Role.seller)
    buyer = await make_user(sessions, "ana", Role.buyer)
    both = await make_listing(
        sessions, seller, "Delivered bread", 3, fulfillment=FulfillmentOption.both
    )
    pickup_only = await make_listing(sessions, seller, "Counter bread", 3)

    async with api(sessions, buyer) as client:
        no_address = await client.post(
            "/api/orders",
            json={"listingId": str(both.id), "quantity": 2, "fulfillment": "delivery"},
        )
        assert no_address.status_code == 422
        refused = await client.post(
            "/api/orders",
            json={
                "listingId": str(pickup_only.id),
                "quantity": 1,
                "fulfillment": "delivery",
                "deliveryAddress": "12 Session Rd, Baguio",
            },
        )
        assert refused.status_code == 400  # that listing is pickup only
        placed = await client.post(
            "/api/orders",
            json={
                "listingId": str(both.id),
                "quantity": 2,
                "fulfillment": "delivery",
                "deliveryAddress": "12 Session Rd, Baguio",
            },
        )
    assert placed.status_code == 201
    order = placed.json()
    assert order["fulfillment"] == "delivery" and order["deliveryStatus"] is None
    assert Decimal(order["total"]) == 100 and Decimal(order["amountDue"]) == 150  # 50 delivery fee

    async with sessions() as db:  # the fee is not part of the commission base
        payment = await db.scalar(select(PaymentTransaction))
        assert payment.amount == 150 and payment.commission == Decimal("7.00")

    path = f"/api/orders/{order['id']}"
    async with api(sessions, seller) as client:
        early = await client.post(f"{path}/delivery", json={"status": "out-for-delivery"})
        assert early.status_code == 409  # not handed over yet
        ready = (await client.post(f"{path}/ready")).json()
        assert ready["deliveryStatus"] == "handed-off" and ready["deliveryReference"].startswith(
            "DLV-"
        )
        by_code = await client.post(f"{path}/picked-up", json={"code": order["pickupCode"]})
        assert by_code.status_code == 409  # delivery orders finish via delivery updates
        skipped = await client.post(f"{path}/delivery", json={"status": "delivered"})
        assert skipped.status_code == 409  # must go out for delivery first
        out = await client.post(f"{path}/delivery", json={"status": "out-for-delivery"})
        assert out.json()["deliveryStatus"] == "out-for-delivery"
        done = (await client.post(f"{path}/delivery", json={"status": "delivered"})).json()
        assert done["status"] == "picked-up" and done["paymentStatus"] == "paid"
        again = await client.post(f"{path}/delivery", json={"status": "delivered"})
        assert again.status_code == 409

    async with api(sessions, buyer) as client:  # a delivered order can be reviewed
        review = await client.post(f"{path}/review", json={"rating": 5})
        assert review.status_code == 201

"""Order placement (UC-10, FR-SYS-6, FR-SYS-7, FR-SYS-8).

The important part is `place_order`: it locks the listing row with
SELECT ... FOR UPDATE before checking stock. If two buyers try to reserve the
last box at the same moment, the second one waits for the first to finish,
then sees the updated quantity and gets a 409 instead of overselling.
"""

import secrets
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.core.config import get_settings
from app.models import (
    Listing,
    ListingStatus,
    Order,
    OrderStatus,
    PaymentStatus,
    PaymentTransaction,
    User,
)
from app.schemas.order import OrderCreate
from app.services import audit
from app.services.notifications import notify

CENT = Decimal("0.01")
# No 0/O or 1/I, so codes are easy to read out at the counter.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_pickup_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


async def get_order_or_404(db: AsyncSession, order_id: uuid.UUID) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id).execution_options(populate_existing=True)
    )
    order = result.unique().scalar_one_or_none()
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    return order


async def place_order(db: AsyncSession, buyer: User, data: OrderCreate) -> tuple[Order, Listing]:
    # Lock only the listing row. lazyload("*") stops SQLAlchemy from joining
    # other tables into the locking query.
    stmt = (
        select(Listing)
        .options(lazyload("*"))
        .where(Listing.id == data.listing_id)
        .with_for_update()
    )
    listing = (await db.execute(stmt)).scalar_one_or_none()

    if listing is None or listing.status != ListingStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item is no longer available.")
    if listing.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_409_CONFLICT, "This item has expired.")
    if listing.seller_id == buyer.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't buy your own listing.")
    if data.quantity > listing.quantity_available:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only {listing.quantity_available} left. Someone may have just reserved some.",
        )

    listing.quantity_available -= data.quantity
    if listing.quantity_available == 0:
        listing.status = ListingStatus.sold_out

    total = (listing.discounted_price * data.quantity).quantize(CENT, ROUND_HALF_UP)
    commission = (total * Decimal(str(get_settings().commission_rate))).quantize(
        CENT, ROUND_HALF_UP
    )

    order = Order(
        buyer_id=buyer.id,
        seller_id=listing.seller_id,
        listing_id=listing.id,
        quantity=data.quantity,
        unit_price=listing.discounted_price,
        original_unit_price=listing.original_price,
        total=total,
        pickup_code=new_pickup_code(),
        status=OrderStatus.reserved,
    )
    db.add(order)
    await db.flush()  # gives order.id

    db.add(
        PaymentTransaction(
            order_id=order.id,
            amount=total,
            commission=commission,
            method=data.payment_method,
            # Simulated: online methods "succeed" instantly; pay-on-pickup waits for handover.
            status=PaymentStatus.pending
            if data.payment_method.value == "pay-on-pickup"
            else PaymentStatus.paid,
            reference=f"SIM-{secrets.token_hex(6).upper()}",
        )
    )

    seller = await db.get(User, listing.seller_id)
    notify(
        db,
        user_id=buyer.id,
        type="order.reserved",
        title="Reservation confirmed",
        body=f"You reserved {data.quantity} × {listing.name}. Pickup code: {order.pickup_code}.",
        link="/buyer/pending",
        email_to=buyer.email,
    )
    if seller is not None:
        notify(
            db,
            user_id=seller.id,
            type="order.received",
            title="New reservation",
            body=f"{buyer.username} reserved {data.quantity} × {listing.name}.",
            link="/seller/handover",
            email_to=seller.email,
        )
    audit.record(
        db,
        actor_id=buyer.id,
        action="order.create",
        entity_type="order",
        entity_id=order.id,
        details={"listing_id": str(listing.id), "quantity": data.quantity, "total": str(total)},
    )

    await db.commit()
    return await get_order_or_404(db, order.id), listing

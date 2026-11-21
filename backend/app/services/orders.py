"""Order placement (UC-10, FR-SYS-6, FR-SYS-7, FR-SYS-8).

The important part is the listing lock: every path that changes stock first runs
SELECT ... FOR UPDATE on the listing row. If two buyers try to reserve the last
box at the same moment, the second one waits for the first to finish, then sees
the updated quantity and gets a 409 instead of overselling.

Lock order (so two requests can never wait on each other):
  - Checkout locks all its listings sorted by id.
  - Cancel locks the order first, then its listing.
  - Nothing locks a listing and then an order.
"""

import secrets
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.core.config import get_settings
from app.models import (
    Listing,
    ListingStatus,
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentTransaction,
    Review,
    User,
)
from app.schemas.order import CheckoutIn, OrderCreate
from app.schemas.review import ReviewCreate
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


async def _lock_listings(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, Listing]:
    """Lock the listing rows (sorted by id) and return them with fresh values."""
    stmt = (
        select(Listing)
        .options(lazyload("*"))  # no joins in a locking query
        .where(Listing.id.in_(ids))
        .order_by(Listing.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {listing.id: listing for listing in (await db.execute(stmt)).scalars()}


async def _lock_order(db: AsyncSession, order_id: uuid.UUID) -> Order | None:
    stmt = (
        select(Order)
        .options(lazyload("*"))
        .where(Order.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _reserve(
    db: AsyncSession, buyer: User, listing: Listing, quantity: int, method: PaymentMethod
) -> Order:
    """Check one locked listing and reserve `quantity` of it. The caller commits."""
    if listing.status != ListingStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{listing.name} is no longer available.")
    if listing.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{listing.name} has expired.")
    if listing.seller_id == buyer.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't buy your own listing.")
    if quantity > listing.quantity_available:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only {listing.quantity_available} of {listing.name} left. "
            "Someone may have just reserved some.",
        )

    listing.quantity_available -= quantity
    if listing.quantity_available == 0:
        listing.status = ListingStatus.sold_out

    total = (listing.discounted_price * quantity).quantize(CENT, ROUND_HALF_UP)
    commission = (total * Decimal(str(get_settings().commission_rate))).quantize(
        CENT, ROUND_HALF_UP
    )

    order = Order(
        buyer_id=buyer.id,
        seller_id=listing.seller_id,
        listing_id=listing.id,
        quantity=quantity,
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
            method=method,
            # Simulated: online methods "succeed" instantly; pay-on-pickup waits for handover.
            status=PaymentStatus.pending
            if method == PaymentMethod.pay_on_pickup
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
        body=f"You reserved {quantity} × {listing.name}. Pickup code: {order.pickup_code}.",
        link="/buyer/pending",
        email_to=buyer.email,
    )
    if seller is not None:
        notify(
            db,
            user_id=seller.id,
            type="order.received",
            title="New reservation",
            body=f"{buyer.username} reserved {quantity} × {listing.name}.",
            link="/seller/handover",
            email_to=seller.email,
        )
    audit.record(
        db,
        actor_id=buyer.id,
        action="order.create",
        entity_type="order",
        entity_id=order.id,
        details={"listing_id": str(listing.id), "quantity": quantity, "total": str(total)},
    )
    return order


async def place_order(db: AsyncSession, buyer: User, data: OrderCreate) -> tuple[Order, Listing]:
    listings = await _lock_listings(db, [data.listing_id])
    listing = listings.get(data.listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item is no longer available.")
    order = await _reserve(db, buyer, listing, data.quantity, data.payment_method)
    await db.commit()
    return await get_order_or_404(db, order.id), listing


async def checkout(db: AsyncSession, buyer: User, data: CheckoutIn) -> list[tuple[Order, Listing]]:
    """Reserve a whole cart in one transaction: every line succeeds or none do."""
    # The same listing twice in a cart becomes one line.
    wanted: dict[uuid.UUID, int] = {}
    for line in data.items:
        wanted[line.listing_id] = wanted.get(line.listing_id, 0) + line.quantity

    listings = await _lock_listings(db, list(wanted))
    if len(listings) != len(wanted):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An item in your cart is no longer available."
        )

    placed: list[tuple[Order, Listing]] = []
    for listing_id, quantity in sorted(wanted.items()):
        listing = listings[listing_id]
        order = await _reserve(db, buyer, listing, quantity, data.payment_method)
        placed.append((order, listing))
    await db.commit()  # an HTTPException above leaves the transaction to get_db's rollback

    return [(await get_order_or_404(db, order.id), listing) for order, listing in placed]


def _own_order_or_404(order: Order | None, *, buyer_id=None, seller_id=None) -> Order:
    if order is None or (buyer_id and order.buyer_id != buyer_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    if seller_id and order.seller_id != seller_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    return order


async def mark_ready(db: AsyncSession, seller: User, order_id: uuid.UUID) -> Order:
    order = _own_order_or_404(await _lock_order(db, order_id), seller_id=seller.id)
    if order.status != OrderStatus.reserved:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"This order is already {order.status.value}."
        )
    order.status = OrderStatus.ready

    buyer = await db.get(User, order.buyer_id)
    listing = await db.get(Listing, order.listing_id)
    if buyer is not None and listing is not None:
        notify(
            db,
            user_id=buyer.id,
            type="order.ready",
            title="Your order is ready",
            body=f"{listing.name} is ready for pickup. Show code {order.pickup_code}.",
            link="/buyer/pending",
            email_to=buyer.email,
        )
    audit.record(
        db, actor_id=seller.id, action="order.ready", entity_type="order", entity_id=order.id
    )
    await db.commit()
    return await get_order_or_404(db, order.id)


async def mark_picked_up(db: AsyncSession, seller: User, order_id: uuid.UUID, code: str) -> Order:
    order = _own_order_or_404(await _lock_order(db, order_id), seller_id=seller.id)
    if order.status not in (OrderStatus.reserved, OrderStatus.ready):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"This order is already {order.status.value}."
        )
    if not secrets.compare_digest(code.strip().upper(), order.pickup_code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That pickup code doesn't match.")

    order.status = OrderStatus.picked_up
    order.picked_up_at = datetime.now(timezone.utc)

    payment = await db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order.id)
    )
    if payment is not None and payment.status == PaymentStatus.pending:
        payment.status = PaymentStatus.paid  # pay-on-pickup is settled at the counter

    notify(
        db,
        user_id=order.buyer_id,
        type="order.picked_up",
        title="Pickup complete",
        body="Thanks for rescuing food! You can now rate your order.",
    )
    audit.record(
        db, actor_id=seller.id, action="order.picked_up", entity_type="order", entity_id=order.id
    )
    await db.commit()
    return await get_order_or_404(db, order.id)


async def cancel_order(db: AsyncSession, buyer: User, order_id: uuid.UUID) -> tuple[Order, Listing]:
    """Buyer cancels a reservation and the quantity goes back on the listing."""
    order = _own_order_or_404(await _lock_order(db, order_id), buyer_id=buyer.id)
    if order.status != OrderStatus.reserved:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only reservations that haven't been prepared can be cancelled.",
        )

    listing = (await _lock_listings(db, [order.listing_id]))[order.listing_id]
    listing.quantity_available += order.quantity
    # A seller may have restocked while this was reserved; keep available <= original.
    listing.original_quantity = max(listing.original_quantity, listing.quantity_available)
    if listing.status == ListingStatus.sold_out and listing.expires_at > datetime.now(timezone.utc):
        listing.status = ListingStatus.active

    order.status = OrderStatus.cancelled
    order.cancelled_at = datetime.now(timezone.utc)

    payment = await db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order.id)
    )
    if payment is not None and payment.status == PaymentStatus.paid:
        payment.status = PaymentStatus.refunded
    elif payment is not None and payment.status == PaymentStatus.pending:
        payment.status = PaymentStatus.failed

    seller = await db.get(User, order.seller_id)
    if seller is not None:
        notify(
            db,
            user_id=seller.id,
            type="order.cancelled",
            title="Reservation cancelled",
            body=f"{buyer.username} cancelled {order.quantity} × {listing.name}.",
            link="/seller/handover",
            email_to=seller.email,
        )
    audit.record(
        db, actor_id=buyer.id, action="order.cancel", entity_type="order", entity_id=order.id
    )
    await db.commit()
    return await get_order_or_404(db, order.id), listing


async def create_review(
    db: AsyncSession, buyer: User, order_id: uuid.UUID, data: ReviewCreate
) -> Review:
    order = _own_order_or_404(await db.get(Order, order_id), buyer_id=buyer.id)
    if order.status != OrderStatus.picked_up:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You can review an order after you've picked it up."
        )
    review = Review(
        order_id=order.id,
        listing_id=order.listing_id,
        buyer_id=buyer.id,
        seller_id=order.seller_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    try:
        await db.commit()  # the unique(order_id) constraint stops double reviews
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You've already reviewed this order."
        ) from exc
    await db.refresh(review)  # loads created_at (server default)
    return review

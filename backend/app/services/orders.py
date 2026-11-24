"""Order placement, delivery and hand-over (UC-10, UC-14, UC-15; FR-SYS-6/7/8/13/14).

Buyers order marketplace listings; partners buy partner offers and claim donations from
the Surplus Board. All of them go through the same locked reservation below.

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
    DeliveryStatus,
    DistributionStatus,
    FulfillmentType,
    Listing,
    ListingChannel,
    ListingStatus,
    Order,
    OrderStatus,
    OrderType,
    PaymentMethod,
    PaymentStatus,
    PaymentTransaction,
    Review,
    User,
)
from app.schemas.order import CheckoutIn, Fulfillment, OrderCreate
from app.schemas.partner import PartnerOrderIn
from app.schemas.review import ReviewCreate
from app.services import audit, delivery
from app.services.listings import lock_listings
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


async def _lock_order(db: AsyncSession, order_id: uuid.UUID) -> Order | None:
    stmt = (
        select(Order)
        .options(lazyload("*"))
        .where(Order.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


# Which listings each kind of order may take (FR-SYS-14).
_CHANNEL_FOR = {
    OrderType.sale: ListingChannel.marketplace,
    OrderType.partner_purchase: ListingChannel.partner_offer,
    OrderType.donation: ListingChannel.donation,
}


def _check_channel(listing: Listing, order_type: OrderType) -> None:
    """Buyers get the marketplace; partners buy partner offers and claim donations."""
    if listing.channel == _CHANNEL_FOR[order_type]:
        return
    if order_type == OrderType.sale:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"{listing.name} is for partners only.")
    if listing.channel == ListingChannel.marketplace:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Partners order from the Surplus Board, not the marketplace.",
        )
    if listing.channel == ListingChannel.donation:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{listing.name} is a free donation. Claim it instead."
        )
    raise HTTPException(
        status.HTTP_409_CONFLICT, f"{listing.name} is a partner offer. Buy it instead."
    )


def _check_fulfillment(listing: Listing, fulfillment: Fulfillment) -> None:
    """The order's pickup or delivery must be one the seller offers (FR-USER-S-12)."""
    if fulfillment.fulfillment_type == FulfillmentType.delivery:
        if not listing.allows_delivery:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{listing.name} is pickup only.")
    elif not listing.allows_pickup:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{listing.name} is delivery only.")


def _orders_page(order_type: OrderType) -> str:
    return "/buyer/pending" if order_type == OrderType.sale else "/partner/orders"


async def _reserve(
    db: AsyncSession,
    buyer: User,
    listing: Listing,
    quantity: int,
    fulfillment: Fulfillment,
    method: PaymentMethod,
    order_type: OrderType = OrderType.sale,
) -> Order:
    """Check one locked listing and reserve `quantity` of it. The caller commits.

    `buyer` is whoever places the order: a buyer, or a partner for partner orders.
    """
    if listing.status != ListingStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{listing.name} is no longer available.")
    if listing.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{listing.name} has expired.")
    if listing.seller_id == buyer.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't buy your own listing.")
    _check_channel(listing, order_type)
    _check_fulfillment(listing, fulfillment)
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
    # Commission is on the food only; the delivery fee is not ours to take a cut of.
    commission = (total * Decimal(str(get_settings().commission_rate))).quantize(
        CENT, ROUND_HALF_UP
    )
    delivering = fulfillment.fulfillment_type == FulfillmentType.delivery
    fee = (listing.delivery_fee or Decimal("0")).quantize(CENT) if delivering else None
    amount = total + (fee or Decimal("0"))

    order = Order(
        buyer_id=buyer.id,
        seller_id=listing.seller_id,
        listing_id=listing.id,
        quantity=quantity,
        unit_price=listing.discounted_price,
        original_unit_price=listing.original_price,
        total=total,
        order_type=order_type,
        fulfillment_type=fulfillment.fulfillment_type,
        delivery_address=fulfillment.delivery_address if delivering else None,
        delivery_fee=fee,
        delivery_status=DeliveryStatus.pending if delivering else None,
        # Partners confirm later that the food reached the people they serve (FR-USER-P-9).
        distribution_status=None if order_type == OrderType.sale else DistributionStatus.pending,
        pickup_code=new_pickup_code(),
        status=OrderStatus.reserved,
    )
    db.add(order)
    await db.flush()  # gives order.id

    pay_later = method in (PaymentMethod.pay_on_pickup, PaymentMethod.cash_on_delivery)
    db.add(
        PaymentTransaction(
            order_id=order.id,
            amount=amount,
            commission=commission,
            method=method,
            # Simulated: online methods "succeed" instantly; cash waits for the handover.
            # A free donation picked up at the shop has nothing to wait for.
            status=PaymentStatus.pending if pay_later and amount > 0 else PaymentStatus.paid,
            reference=f"SIM-{secrets.token_hex(6).upper()}",
        )
    )

    seller = await db.get(User, listing.seller_id)
    if delivering:
        how = f"It will be delivered to {order.delivery_address}. "
    elif order_type != OrderType.sale:
        hold = get_settings().claim_hold_hours
        how = f"Collect it within {hold} hours or it goes back on the Surplus Board. "
    else:
        how = "Pick it up at the shop. "
    notify(
        db,
        user_id=buyer.id,
        type="order.reserved",
        title="Donation claimed" if order_type == OrderType.donation else "Reservation confirmed",
        body=f"You reserved {quantity} × {listing.name}. {how}Order code: {order.pickup_code}.",
        link=_orders_page(order_type),
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
        details={
            "listing_id": str(listing.id),
            "quantity": quantity,
            "total": str(total),
            "order_type": order_type.value,
            "fulfillment": fulfillment.fulfillment_type.value,
        },
    )
    return order


async def place_order(db: AsyncSession, buyer: User, data: OrderCreate) -> tuple[Order, Listing]:
    listings = await lock_listings(db, [data.listing_id])
    listing = listings.get(data.listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item is no longer available.")
    order = await _reserve(db, buyer, listing, data.quantity, data, data.payment_method)
    await db.commit()
    return await get_order_or_404(db, order.id), listing


async def place_partner_order(
    db: AsyncSession,
    partner: User,
    listing_id: uuid.UUID,
    data: PartnerOrderIn,
    order_type: OrderType,
) -> tuple[Order, Listing]:
    """A partner buys a partner offer or claims a donation (UC-14, UC-15).

    The listing row is locked like any other order, so two partners can never both
    claim the last donation: the second one waits, then gets a 409.
    """
    listings = await lock_listings(db, [listing_id])
    listing = listings.get(listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item is no longer available.")
    # Partners settle in cash at the handover; free pickups are marked paid straight away.
    method = (
        PaymentMethod.cash_on_delivery
        if data.fulfillment_type == FulfillmentType.delivery
        else PaymentMethod.pay_on_pickup
    )
    order = await _reserve(db, partner, listing, data.quantity, data, method, order_type)
    await db.commit()
    return await get_order_or_404(db, order.id), listing


async def checkout(db: AsyncSession, buyer: User, data: CheckoutIn) -> list[tuple[Order, Listing]]:
    """Reserve a whole cart in one transaction: every line succeeds or none do."""
    # The same listing twice in a cart becomes one line.
    wanted: dict[uuid.UUID, int] = {}
    for line in data.items:
        wanted[line.listing_id] = wanted.get(line.listing_id, 0) + line.quantity

    listings = await lock_listings(db, list(wanted))
    if len(listings) != len(wanted):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An item in your cart is no longer available."
        )

    placed: list[tuple[Order, Listing]] = []
    for listing_id, quantity in sorted(wanted.items()):
        listing = listings[listing_id]
        order = await _reserve(db, buyer, listing, quantity, data, data.payment_method)
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
    delivering = order.fulfillment_type == FulfillmentType.delivery
    if delivering:  # simulated hand-off to the courier
        order.delivery_status = DeliveryStatus.preparing

    buyer = await db.get(User, order.buyer_id)
    listing = await db.get(Listing, order.listing_id)
    if buyer is not None and listing is not None:
        notify(
            db,
            user_id=buyer.id,
            type="order.ready",
            title="Your order is with the courier" if delivering else "Your order is ready",
            body=f"{listing.name} was packed and handed to the courier."
            if delivering
            else f"{listing.name} is ready for pickup. Show code {order.pickup_code}.",
            link=_orders_page(order.order_type),
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
    if order.fulfillment_type == FulfillmentType.delivery:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Delivery orders finish when the delivery is marked delivered.",
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


async def update_delivery(
    db: AsyncSession, seller: User, order_id: uuid.UUID, new_status: DeliveryStatus
) -> Order:
    """Move a delivery along: out-for-delivery, then delivered (FR-SYS-13, simulated)."""
    order = _own_order_or_404(await _lock_order(db, order_id), seller_id=seller.id)
    current = order.delivery_status
    if order.fulfillment_type != FulfillmentType.delivery or current is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This is not a delivery order.")
    if current == DeliveryStatus.pending:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Mark the order ready first to hand it to the courier."
        )
    if delivery.NEXT_STATUS.get(current) != new_status:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A delivery can't go from {current.value} to {new_status.value}.",
        )
    order.delivery_status = new_status

    if new_status == DeliveryStatus.delivered:
        order.status = OrderStatus.delivered
        order.delivered_at = datetime.now(timezone.utc)
        payment = await db.scalar(
            select(PaymentTransaction).where(PaymentTransaction.order_id == order.id)
        )
        if payment is not None and payment.status == PaymentStatus.pending:
            payment.status = PaymentStatus.paid  # cash on delivery is settled at the door

    notify(
        db,
        user_id=order.buyer_id,
        type=f"order.{new_status.value}",
        title="Your order was delivered"
        if new_status == DeliveryStatus.delivered
        else "Your order is out for delivery",
        body=f"Order code: {order.pickup_code}.",
        link=_orders_page(order.order_type),
    )
    audit.record(
        db,
        actor_id=seller.id,
        action=f"order.delivery.{new_status.value}",
        entity_type="order",
        entity_id=order.id,
    )
    await db.commit()
    return await get_order_or_404(db, order.id)


async def mark_distributed(db: AsyncSession, partner: User, order_id: uuid.UUID) -> Order:
    """The partner confirms the food reached the people it serves (FR-USER-P-9)."""
    order = _own_order_or_404(await _lock_order(db, order_id), buyer_id=partner.id)
    if order.order_type == OrderType.sale:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only partner orders are distributed.")
    if order.status not in (OrderStatus.picked_up, OrderStatus.delivered):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Collect or receive the order before distributing it."
        )
    if order.distribution_status == DistributionStatus.distributed:
        raise HTTPException(status.HTTP_409_CONFLICT, "This order is already distributed.")

    order.distribution_status = DistributionStatus.distributed
    order.distributed_at = datetime.now(timezone.utc)
    notify(
        db,
        user_id=order.seller_id,
        type="order.distributed",
        title="Your surplus reached people in need",
        body=f"{partner.username} handed out {order.quantity} items from your shop.",
    )
    audit.record(
        db, actor_id=partner.id, action="order.distributed", entity_type="order", entity_id=order.id
    )
    await db.commit()
    return await get_order_or_404(db, order.id)


async def _cancel_and_restock(db: AsyncSession, order: Order) -> Listing:
    """Cancel a locked order, refund its payment and put the quantity back on the listing."""
    listing = (await lock_listings(db, [order.listing_id]))[order.listing_id]
    listing.quantity_available += order.quantity
    # A seller may have restocked while this was reserved; keep available <= original.
    listing.original_quantity = max(listing.original_quantity, listing.quantity_available)
    if listing.status == ListingStatus.sold_out and listing.expires_at > datetime.now(timezone.utc):
        listing.status = ListingStatus.active

    order.status = OrderStatus.cancelled
    order.cancelled_at = datetime.now(timezone.utc)
    if order.delivery_status is not None:
        order.delivery_status = DeliveryStatus.cancelled

    payment = await db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order.id)
    )
    if payment is not None and payment.status == PaymentStatus.paid:
        payment.status = PaymentStatus.refunded
    elif payment is not None and payment.status == PaymentStatus.pending:
        payment.status = PaymentStatus.failed
    return listing


async def release_claim(db: AsyncSession, order_id: uuid.UUID) -> Listing | None:
    """Give an uncollected partner order's stock back (used by the scheduled job).

    Returns the listing, or None if the order was collected or cancelled in the meantime.
    """
    order = await _lock_order(db, order_id)
    if (
        order is None
        or order.order_type == OrderType.sale
        or order.status not in (OrderStatus.reserved, OrderStatus.ready)
        or order.fulfillment_type != FulfillmentType.pickup
    ):
        return None

    listing = await _cancel_and_restock(db, order)
    hold = get_settings().claim_hold_hours
    partner = await db.get(User, order.buyer_id)
    name = (
        partner.partner_profile.organization_name
        if partner and partner.partner_profile
        else "A partner"
    )
    notify(
        db,
        user_id=order.buyer_id,
        type="order.released",
        title="Order released",
        body=(
            f"{order.quantity} × {listing.name} wasn't collected within {hold} hours, "
            "so it went back on the Surplus Board."
        ),
        link=_orders_page(order.order_type),
    )
    notify(
        db,
        user_id=order.seller_id,
        type="order.released",
        title="Stock returned",
        body=(
            f"{name} didn't collect {order.quantity} × {listing.name}. "
            "It's back on the Surplus Board."
        ),
        link=f"/seller/manage?listing={listing.id}",
    )
    audit.record(
        db,
        actor_id=None,
        action="order.release",
        entity_type="order",
        entity_id=order.id,
        details={"listing_id": str(listing.id), "quantity": order.quantity},
    )
    await db.commit()
    return listing


async def cancel_order(db: AsyncSession, buyer: User, order_id: uuid.UUID) -> tuple[Order, Listing]:
    """Buyer cancels a reservation and the quantity goes back on the listing."""
    order = _own_order_or_404(await _lock_order(db, order_id), buyer_id=buyer.id)
    if order.status != OrderStatus.reserved:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only reservations that haven't been prepared can be cancelled.",
        )

    listing = await _cancel_and_restock(db, order)

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
    if order.status not in (OrderStatus.picked_up, OrderStatus.delivered):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You can review an order after you've received it."
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

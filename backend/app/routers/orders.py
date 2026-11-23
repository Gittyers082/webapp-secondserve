"""Orders: reserve, track, hand over (UC-10, UC-11).

Owner: Role 3 (Backend Developer, Marketplace & Orders).
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.deps import DB, ActiveBuyer, ActiveSeller, CurrentUser
from app.core.rate_limit import limiter
from app.models import DeliveryStatus, Order, OrderStatus, Role, User
from app.realtime.stock import stock
from app.schemas.order import CheckoutIn, DeliveryUpdateIn, OrderCreate, OrderOut, PickupIn
from app.schemas.review import ReviewCreate, ReviewOut
from app.services import orders as order_service
from app.services import receipts
from app.services.orders import get_order_or_404, place_order

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def reserve(request: Request, data: OrderCreate, db: DB, buyer: ActiveBuyer) -> OrderOut:
    """Reserve an item for pickup. Returns 409 if someone else got the last ones."""
    order, listing = await place_order(db, buyer, data)
    await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return OrderOut.from_model(order)


@router.get("/mine", response_model=list[OrderOut])
async def my_orders(
    db: DB,
    user: CurrentUser,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
) -> list[OrderOut]:
    """Buyers see orders they placed; sellers see orders they received (UC-11)."""
    owner_column = Order.seller_id if user.role == Role.seller else Order.buyer_id
    stmt = select(Order).where(owner_column == user.id).order_by(Order.created_at.desc())
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    rows = await db.execute(stmt)
    return [OrderOut.from_model(order) for order in rows.unique().scalars()]


@router.get("/{order_id}", response_model=OrderOut)
async def order_detail(order_id: uuid.UUID, db: DB, user: CurrentUser) -> OrderOut:
    order = await get_order_or_404(db, order_id)
    if user.id not in (order.buyer_id, order.seller_id) and user.role != Role.admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")  # NFR-SYS-S-3
    return OrderOut.from_model(order)


@router.post("/checkout", response_model=list[OrderOut], status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def checkout(
    request: Request, data: CheckoutIn, db: DB, buyer: ActiveBuyer
) -> list[OrderOut]:
    """Reserve every cart line in one transaction. If any line fails, nothing is reserved."""
    placed = await order_service.checkout(db, buyer, data)
    for _, listing in placed:
        await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return [OrderOut.from_model(order) for order, _ in placed]


@router.post("/{order_id}/ready", response_model=OrderOut)
async def ready(order_id: uuid.UUID, db: DB, seller: ActiveSeller) -> OrderOut:
    """Seller has the order set aside; tells the buyer."""
    return OrderOut.from_model(await order_service.mark_ready(db, seller, order_id))


@router.post("/{order_id}/picked-up", response_model=OrderOut)
@limiter.limit("10/minute")
async def picked_up(
    request: Request, order_id: uuid.UUID, data: PickupIn, db: DB, seller: ActiveSeller
) -> OrderOut:
    """Seller enters the buyer's pickup code at the counter."""
    order = await order_service.mark_picked_up(db, seller, order_id, data.code)
    return OrderOut.from_model(order)


@router.post("/{order_id}/delivery", response_model=OrderOut)
async def delivery_update(
    order_id: uuid.UUID, data: DeliveryUpdateIn, db: DB, seller: ActiveSeller
) -> OrderOut:
    """Move a delivery order along: out-for-delivery, then delivered (simulated courier)."""
    order = await order_service.update_delivery(db, seller, order_id, DeliveryStatus(data.status))
    return OrderOut.from_model(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel(order_id: uuid.UUID, db: DB, buyer: ActiveBuyer) -> OrderOut:
    """Buyer cancels a reservation; the quantity goes back on sale."""
    order, listing = await order_service.cancel_order(db, buyer, order_id)
    await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return OrderOut.from_model(order)


@router.post("/{order_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def review(order_id: uuid.UUID, data: ReviewCreate, db: DB, buyer: ActiveBuyer) -> ReviewOut:
    """Rate an order after pickup (FR-USER-B-15). One review per order."""
    created = await order_service.create_review(db, buyer, order_id, data)
    return ReviewOut(
        id=created.id,
        order_id=created.order_id,
        listing_id=created.listing_id,
        author=buyer.username,
        rating=created.rating,
        comment=created.comment,
        created_at=created.created_at,
    )


@router.get("/{order_id}/receipt", response_class=HTMLResponse)
async def receipt(order_id: uuid.UUID, db: DB, user: CurrentUser) -> HTMLResponse:
    """A printable receipt for the buyer, partner or seller of the order (FR-USER-S-11, B-13).

    The browser's Print dialog saves it as a PDF.
    """
    order = await get_order_or_404(db, order_id)
    if user.id not in (order.buyer_id, order.seller_id) and user.role != Role.admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")  # NFR-SYS-S-3
    customer = await db.get(User, order.buyer_id)
    return HTMLResponse(receipts.render(order, customer))

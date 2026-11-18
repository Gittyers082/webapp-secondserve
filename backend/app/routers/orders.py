"""Orders: reserve, track, hand over (UC-10, UC-11).

Owner: Role 3 (Backend Developer, Marketplace & Orders).
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.core.deps import DB, ActiveBuyer, CurrentUser
from app.core.rate_limit import limiter
from app.models import Order, OrderStatus, Role
from app.realtime.stock import stock
from app.schemas.order import OrderCreate, OrderOut
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


# TODO(Role 3): POST /api/orders/checkout — reserve every cart line in ONE transaction
#   (lock listings in id order to avoid deadlocks); all succeed or none do.
# TODO(Role 3): POST /api/orders/{id}/ready      — seller marks it ready; notify buyer.
# TODO(Role 3): POST /api/orders/{id}/picked-up  — seller enters the buyer's pickup code;
#   mark payment paid, set picked_up_at; notify buyer (seller /handover screen).
# TODO(Role 3): POST /api/orders/{id}/cancel     — buyer cancels while reserved; put the
#   quantity back on the listing (lock it first) and publish the new stock.
# TODO(Role 3): POST /api/orders/{id}/review     — after pickup only (FR-USER-B-15).
# TODO(Role 1): GET /api/orders/{id}/receipt     — PDF/HTML receipt (FR-USER-S-11, B-13).

"""Partner Surplus Board: surplus offers and donations (UC-13 to UC-15).

Owners: Role 3 (buying, claiming, offering, distribution) and Role 4 (the screens).
Buying and claiming go through the same locked reservation as buyer orders
(services/orders.py), so two partners can't both get the last item.
Ported from Ethan's backend-updates branch onto the channel model.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.deps import DB, ActivePartner, ActiveSeller
from app.models import FoodCategory, Listing, ListingChannel, ListingStatus, Order, OrderType
from app.realtime.stock import stock
from app.schemas.common import Page
from app.schemas.listing import ListingOut, SortOption
from app.schemas.order import OrderOut
from app.schemas.partner import OfferToPartnersIn, PartnerOrderIn
from app.services import audit
from app.services import orders as order_service
from app.services.listings import ensure_eligible, get_listing_or_404, lock_listings
from app.services.search import listing_query, sort_clauses

router = APIRouter(tags=["partners"])

_PARTNER_CHANNELS = (ListingChannel.partner_offer, ListingChannel.donation)


@router.get("/api/partners/surplus", response_model=Page[ListingOut])
async def surplus_board(
    db: DB,
    partner: ActivePartner,
    q: str | None = Query(default=None, max_length=100, description="Search name or shop"),
    channel: ListingChannel | None = None,
    category: FoodCategory | None = None,
    max_price: Decimal | None = Query(default=None, alias="maxPrice", ge=0),
    min_quantity: int | None = Query(default=None, alias="minQuantity", ge=1),
    expiring_soon: bool = Query(
        default=False,
        alias="expiringSoon",
        description="Only items expiring within SURPLUS_WINDOW_HOURS",
    ),
    expires_before: datetime | None = Query(default=None, alias="expiresBefore"),
    sort: SortOption = "expiring",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[ListingOut]:
    """Unsold items offered to partners, soonest to expire first (FR-USER-P-4).

    TODO(Role 3): filter by distance from the partner's address.
    """
    if channel is not None and channel not in _PARTNER_CHANNELS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick partner-offer or donation.")
    if expiring_soon:
        soon = datetime.now(timezone.utc) + timedelta(hours=get_settings().surplus_window_hours)
        expires_before = min(expires_before, soon) if expires_before else soon

    stmt = listing_query(
        channels=(channel,) if channel else _PARTNER_CHANNELS,
        q=q,
        category=category,
        max_price=max_price,
        min_quantity=min_quantity,
        expires_before=expires_before,
    )
    total = await db.scalar(stmt.with_only_columns(func.count(Listing.id)).order_by(None))
    rows = await db.execute(stmt.order_by(*sort_clauses(sort, q)).limit(limit).offset(offset))
    items = [ListingOut.from_model(listing) for listing in rows.unique().scalars()]
    return Page(items=items, total=total or 0, limit=limit, offset=offset)


@router.get("/api/partners/orders", response_model=list[OrderOut])
async def my_partner_orders(db: DB, partner: ActivePartner) -> list[OrderOut]:
    """Items this partner bought or claimed, newest first (FR-USER-P-9)."""
    rows = await db.execute(
        select(Order).where(Order.buyer_id == partner.id).order_by(Order.created_at.desc())
    )
    return [OrderOut.from_model(order) for order in rows.unique().scalars()]


@router.post(
    "/api/partners/surplus/{listing_id}/buy",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
async def buy_surplus(
    listing_id: uuid.UUID, data: PartnerOrderIn, db: DB, partner: ActivePartner
) -> OrderOut:
    """A partner buys a partner offer at its partner price (UC-14, FR-USER-P-5).

    TODO(Role 3): decide with the team whether only LGU and government-agency partners
    may buy (FR-USER-P-5), and check `partner.partner_profile.organization_type` if so.
    """
    order, listing = await order_service.place_partner_order(
        db, partner, listing_id, data, OrderType.partner_purchase
    )
    await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return OrderOut.from_model(order)


@router.post(
    "/api/partners/surplus/{listing_id}/claim",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
async def claim_donation(
    listing_id: uuid.UUID, data: PartnerOrderIn, db: DB, partner: ActivePartner
) -> OrderOut:
    """A partner claims a free donation (UC-15, FR-USER-P-6).

    TODO(Role 1): release claims that aren't collected in time (a Celery job).
    """
    order, listing = await order_service.place_partner_order(
        db, partner, listing_id, data, OrderType.donation
    )
    await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return OrderOut.from_model(order)


@router.post("/api/partners/orders/{order_id}/distributed", response_model=OrderOut)
async def mark_distributed(order_id: uuid.UUID, db: DB, partner: ActivePartner) -> OrderOut:
    """The partner confirms the items reached people in need (FR-USER-P-9)."""
    order = await order_service.mark_distributed(db, partner, order_id)
    return OrderOut.from_model(order)


@router.post("/api/listings/{listing_id}/offer-to-partners", response_model=ListingOut)
async def offer_to_partners(
    listing_id: uuid.UUID,
    data: OfferToPartnersIn,
    request: Request,
    db: DB,
    seller: ActiveSeller,
) -> ListingOut:
    """A seller moves an unsold listing to the Surplus Board (UC-13, FR-USER-S-13).

    The listing leaves the marketplace for good: its price becomes the partner price
    (0 for a donation). Reservations already made keep the price they were made at.

    TODO(Role 1): notify partners about new surplus (the notification helper).
    """
    # Lock it so a buyer reserving at the old price can't slip in during the switch.
    listing = (await lock_listings(db, [listing_id])).get(listing_id)
    if listing is None or listing.seller_id != seller.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This listing no longer exists.")
    if listing.status != ListingStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only active listings can be offered.")
    if listing.channel != ListingChannel.marketplace:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This listing is already on the Surplus Board."
        )

    if data.channel == "donation":
        price = Decimal("0")
    else:
        price = data.partner_price or Decimal("0")
        if price <= 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                ["A free offer is a donation. Choose donation instead."],
            )
        if price >= listing.discounted_price:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                ["The partner price must be lower than the current price."],
            )

    listing.channel = ListingChannel(data.channel)
    listing.discounted_price = price
    listing.surplus_at = datetime.now(timezone.utc)
    ensure_eligible(listing)
    audit.record(
        db,
        actor_id=seller.id,
        action=f"listing.offer.{data.channel}",
        entity_type="listing",
        entity_id=listing.id,
        details={"price": str(price)},
        request=request,
    )
    await db.commit()
    return ListingOut.from_model(await get_listing_or_404(db, listing.id))

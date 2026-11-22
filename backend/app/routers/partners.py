"""Partner Surplus Board: surplus offers and donations (UC-13 to UC-15).

Owners: Role 3 (buying, claiming, offering, distribution) and Role 4 (the screens).
The two read routes work now so the partner screens can be built against real data;
the write routes return 501 until they are implemented.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import DB, ActivePartner, ActiveSeller
from app.models import FoodCategory, Listing, ListingChannel, ListingStatus, Order
from app.schemas.common import Page
from app.schemas.listing import ListingOut
from app.schemas.order import OrderOut
from app.schemas.partner import OfferToPartnersIn, PartnerOrderIn

router = APIRouter(tags=["partners"])

_PARTNER_CHANNELS = (ListingChannel.partner_offer, ListingChannel.donation)


def _not_yet(what: str) -> HTTPException:
    return HTTPException(status.HTTP_501_NOT_IMPLEMENTED, f"{what} is not built yet.")


@router.get("/api/partners/surplus", response_model=Page[ListingOut])
async def surplus_board(
    db: DB,
    partner: ActivePartner,
    channel: ListingChannel | None = None,
    category: FoodCategory | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[ListingOut]:
    """Unsold items offered to partners, soonest to expire first (FR-USER-P-4).

    TODO(Role 3): filter by distance from the partner's address and by time left.
    """
    now = datetime.now(timezone.utc)
    stmt = select(Listing).where(
        Listing.status == ListingStatus.active,
        Listing.expires_at > now,
        Listing.channel.in_(_PARTNER_CHANNELS),
    )
    if channel is not None:
        if channel not in _PARTNER_CHANNELS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick partner-offer or donation.")
        stmt = stmt.where(Listing.channel == channel)
    if category is not None:
        stmt = stmt.where(Listing.category == category)

    total = await db.scalar(stmt.with_only_columns(func.count(Listing.id)).order_by(None))
    rows = await db.execute(stmt.order_by(Listing.expires_at.asc()).limit(limit).offset(offset))
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
    """An agency buys a partner offer at its partner price (UC-14, FR-USER-P-5).

    TODO(Role 3): only for LGU and government-agency partners; lock the listing like
    `services.orders._reserve`; create an Order with `order_type=partner-purchase` and
    `distribution_status=pending`; simulated payment; notify the seller.
    """
    raise _not_yet("Buying surplus")


@router.post(
    "/api/partners/surplus/{listing_id}/claim",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
async def claim_donation(
    listing_id: uuid.UUID, data: PartnerOrderIn, db: DB, partner: ActivePartner
) -> OrderOut:
    """A charity or shelter claims a free donation (UC-15, FR-USER-P-6).

    TODO(Role 3): lock the listing so two partners can't claim the same item; create an
    Order with `order_type=donation`, total 0 and `distribution_status=pending`; notify
    the seller; release the claim if it isn't collected in time.
    """
    raise _not_yet("Claiming donations")


@router.post("/api/partners/orders/{order_id}/distributed", response_model=OrderOut)
async def mark_distributed(order_id: uuid.UUID, db: DB, partner: ActivePartner) -> OrderOut:
    """The partner confirms the items reached people in need (FR-USER-P-9).

    TODO(Role 3): only the partner's own received orders; set `distribution_status`
    to distributed and `distributed_at`; record it for the impact reports.
    """
    raise _not_yet("Marking items as distributed")


@router.post("/api/listings/{listing_id}/offer-to-partners", response_model=ListingOut)
async def offer_to_partners(
    listing_id: uuid.UUID, data: OfferToPartnersIn, db: DB, seller: ActiveSeller
) -> ListingOut:
    """A seller moves an unsold listing to the Surplus Board (UC-13, FR-USER-S-13).

    TODO(Role 3): only the seller's own active listing; set `channel`, `surplus_at` and
    the partner price (0 for donations); publish the stock change; notify partners
    (Role 1's notification helper).
    """
    raise _not_yet("Offering listings to partners")

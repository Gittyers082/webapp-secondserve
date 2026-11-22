"""Partner Surplus Board (UC-14, UC-15, FR-USER-P-4). Owner: Role 3.

Partners browse listings that sellers moved here as partner offers or donations, then
order them through POST /api/orders (or /checkout), the same locked path buyers use.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import func

from app.core.config import get_settings
from app.core.deps import DB, ActivePartner
from app.models import FoodCategory, Listing, ListingKind
from app.schemas.common import Page
from app.schemas.listing import ListingOut, SortOption
from app.services.search import listing_query, sort_clauses

router = APIRouter(prefix="/api/surplus", tags=["surplus"])


@router.get("", response_model=Page[ListingOut])
async def surplus_board(
    db: DB,
    partner: ActivePartner,
    q: str | None = Query(default=None, max_length=100, description="Search name or shop"),
    kind: Literal["partner-offer", "donation"] | None = None,
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
    """Partner offers and donations that are still active, most urgent first by default."""
    if expiring_soon:
        soon = datetime.now(timezone.utc) + timedelta(hours=get_settings().surplus_window_hours)
        expires_before = min(expires_before, soon) if expires_before else soon

    kinds = (ListingKind(kind),) if kind else (ListingKind.partner_offer, ListingKind.donation)
    stmt = listing_query(
        kinds=kinds,
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

"""Listing search shared by the marketplace feed and the partner Surplus Board.

pg_trgm gives typo-tolerant matching; the trigram index on listings.name keeps it fast.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, func, or_, select

from app.models import FoodCategory, Listing, ListingKind, ListingStatus, SellerProfile

discount = 1 - Listing.discounted_price / Listing.original_price
SORTS = {
    "newest": Listing.created_at.desc(),
    "price-asc": Listing.discounted_price.asc(),
    "price-desc": Listing.discounted_price.desc(),
    "discount": discount.desc(),
    "expiring": Listing.expires_at.asc(),
}


def listing_query(
    *,
    kinds: tuple[ListingKind, ...],
    q: str | None = None,
    category: FoodCategory | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    min_discount: int | None = None,
    min_quantity: int | None = None,
    expires_before: datetime | None = None,
) -> Select:
    """Active, unexpired listings of the given kinds, with the filters applied."""
    stmt = (
        select(Listing)
        .join(SellerProfile, SellerProfile.user_id == Listing.seller_id)
        .where(
            Listing.status == ListingStatus.active,
            Listing.expires_at > datetime.now(timezone.utc),
            Listing.kind.in_(kinds),
        )
    )
    if q:
        # Substring match, or pg_trgm's "similar enough" (%) so small typos still find things.
        stmt = stmt.where(
            or_(
                Listing.name.icontains(q, autoescape=True),
                SellerProfile.business_name.icontains(q, autoescape=True),
                Listing.name.op("%")(q),
                SellerProfile.business_name.op("%")(q),
            )
        )
    if category:
        stmt = stmt.where(Listing.category == category)
    if min_price is not None:
        stmt = stmt.where(Listing.discounted_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.discounted_price <= max_price)
    if min_discount is not None:
        stmt = stmt.where(discount * 100 >= min_discount)
    if min_quantity is not None:
        stmt = stmt.where(Listing.quantity_available >= min_quantity)
    if expires_before is not None:
        stmt = stmt.where(Listing.expires_at <= expires_before)
    return stmt


def sort_clauses(sort: str, q: str | None) -> tuple:
    if sort == "relevance" and q:
        score = func.greatest(
            func.similarity(Listing.name, q), func.similarity(SellerProfile.business_name, q)
        )
        return (score.desc(), Listing.created_at.desc())
    return (SORTS.get(sort, Listing.created_at.desc()),)

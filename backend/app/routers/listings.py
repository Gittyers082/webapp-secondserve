"""Listings: browse, search, create, edit, withdraw.

Owner: Role 3 (Backend Developer, Marketplace & Orders).
This file is the worked example the rest of the API follows:
schemas in, eligibility check, audit record, commit, schema out.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from app.core.deps import DB, ActiveSeller
from app.models import FoodCategory, Listing, ListingStatus, Order, OrderStatus, SellerProfile
from app.realtime.stock import stock
from app.schemas.common import Page
from app.schemas.listing import (
    ListingCreate,
    ListingOut,
    ListingStatusIn,
    ListingUpdate,
    SortOption,
)
from app.services import audit
from app.services.listings import ensure_eligible, get_listing_or_404

router = APIRouter(prefix="/api/listings", tags=["listings"])

_discount = 1 - Listing.discounted_price / Listing.original_price
_SORTS = {
    "newest": Listing.created_at.desc(),
    "price-asc": Listing.discounted_price.asc(),
    "price-desc": Listing.discounted_price.desc(),
    "discount": _discount.desc(),
    "expiring": Listing.expires_at.asc(),
}


@router.get("", response_model=Page[ListingOut])
async def browse(
    db: DB,
    q: str | None = Query(default=None, max_length=100, description="Search name or shop"),
    category: FoodCategory | None = None,
    min_price: Decimal | None = Query(default=None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(default=None, alias="maxPrice", ge=0),
    min_discount: int | None = Query(default=None, alias="minDiscount", ge=0, le=100),
    expires_before: datetime | None = Query(default=None, alias="expiresBefore"),
    sort: SortOption = "newest",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[ListingOut]:
    """Public marketplace feed (UC-07, UC-08, FR-USER-B-4/5/6). Only active, unexpired items."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Listing)
        .join(SellerProfile, SellerProfile.user_id == Listing.seller_id)
        .where(Listing.status == ListingStatus.active, Listing.expires_at > now)
    )
    if q:
        # TODO(Role 3): rank by pg_trgm similarity() for typo-tolerant search.
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(Listing.name.ilike(pattern), SellerProfile.business_name.ilike(pattern))
        )
    if category:
        stmt = stmt.where(Listing.category == category)
    if min_price is not None:
        stmt = stmt.where(Listing.discounted_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.discounted_price <= max_price)
    if min_discount is not None:
        stmt = stmt.where(_discount * 100 >= min_discount)
    if expires_before is not None:
        stmt = stmt.where(Listing.expires_at <= expires_before)

    total = await db.scalar(stmt.with_only_columns(func.count(Listing.id)).order_by(None))
    rows = await db.execute(stmt.order_by(_SORTS[sort]).limit(limit).offset(offset))
    items = [ListingOut.from_model(listing) for listing in rows.unique().scalars()]
    return Page(items=items, total=total or 0, limit=limit, offset=offset)


@router.get("/mine", response_model=list[ListingOut])
async def my_listings(db: DB, seller: ActiveSeller) -> list[ListingOut]:
    """Seller dashboard and Manage Listings (UC-06, FR-USER-S-8)."""
    rows = await db.execute(
        select(Listing).where(Listing.seller_id == seller.id).order_by(Listing.created_at.desc())
    )
    return [ListingOut.from_model(listing) for listing in rows.unique().scalars()]


@router.get("/{listing_id}", response_model=ListingOut)
async def listing_detail(listing_id: uuid.UUID, db: DB) -> ListingOut:
    """Listing details (UC-09). Returns removed/sold-out items too, so the UI can say so."""
    return ListingOut.from_model(await get_listing_or_404(db, listing_id))


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    request: Request, data: ListingCreate, db: DB, seller: ActiveSeller
) -> ListingOut:
    """Create a listing (UC-03, FR-USER-S-4)."""
    pickup = data.pickup_location or (
        seller.seller_profile.business_address if seller.seller_profile else None
    )
    if not pickup:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, ["Add a pickup location."])

    listing = Listing(
        seller_id=seller.id,
        name=data.name,
        description=data.description,
        category=data.category,
        original_price=data.original_price,
        discounted_price=data.discounted_price,
        quantity_available=data.quantity,
        original_quantity=data.quantity,
        expires_at=data.expires_at,
        pickup_location=pickup,
        art=data.art,
        status=ListingStatus.active,
    )
    ensure_eligible(listing)
    db.add(listing)
    await db.flush()
    audit.record(
        db,
        actor_id=seller.id,
        action="listing.create",
        entity_type="listing",
        entity_id=listing.id,
        request=request,
    )
    await db.commit()
    return ListingOut.from_model(await get_listing_or_404(db, listing.id))


@router.patch("/{listing_id}", response_model=ListingOut)
async def edit_listing(
    listing_id: uuid.UUID, data: ListingUpdate, db: DB, seller: ActiveSeller
) -> ListingOut:
    """Edit an active listing (UC-04, FR-USER-S-5)."""
    listing = await _own_listing(db, listing_id, seller.id)
    if listing.status != ListingStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only active listings can be edited.")

    changes = data.model_dump(exclude_unset=True)
    if "quantity" in changes:
        new_quantity = changes.pop("quantity")
        # Restocking raises the ceiling too, so the DB check (available <= original) holds.
        listing.original_quantity = max(listing.original_quantity, new_quantity)
        listing.quantity_available = new_quantity
    for field, value in changes.items():
        setattr(listing, field, value)

    ensure_eligible(listing)
    audit.record(
        db,
        actor_id=seller.id,
        action="listing.update",
        entity_type="listing",
        entity_id=listing.id,
        details={"fields": sorted(data.model_dump(exclude_unset=True))},
    )
    await db.commit()
    await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return ListingOut.from_model(await get_listing_or_404(db, listing.id))


@router.post("/{listing_id}/status", response_model=ListingOut)
async def set_status(
    listing_id: uuid.UUID, data: ListingStatusIn, db: DB, seller: ActiveSeller
) -> ListingOut:
    """Mark sold out, withdraw, or reactivate (FR-USER-S-7, UC-05)."""
    listing = await _own_listing(db, listing_id, seller.id)
    if listing.status in (ListingStatus.removed, ListingStatus.expired):
        raise HTTPException(status.HTTP_409_CONFLICT, "This listing can't be changed anymore.")
    new_status = ListingStatus(data.status)
    if new_status == ListingStatus.active:
        ensure_eligible(listing)
    listing.status = new_status
    audit.record(
        db,
        actor_id=seller.id,
        action=f"listing.{data.status}",
        entity_type="listing",
        entity_id=listing.id,
    )
    await db.commit()
    await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return ListingOut.from_model(await get_listing_or_404(db, listing.id))


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(listing_id: uuid.UUID, db: DB, seller: ActiveSeller) -> None:
    """Delete a listing (FR-USER-S-6). Listings with past orders are withdrawn to keep history."""
    listing = await _own_listing(db, listing_id, seller.id)
    open_orders = await db.scalar(
        select(func.count()).where(
            Order.listing_id == listing.id,
            Order.status.in_([OrderStatus.reserved, OrderStatus.ready]),
        )
    )
    if open_orders:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{open_orders} reservation(s) are still waiting for pickup. Hand them over first.",
        )
    any_orders = await db.scalar(select(func.count()).where(Order.listing_id == listing.id))
    if any_orders:
        listing.status = ListingStatus.withdrawn
    else:
        await db.delete(listing)
    audit.record(
        db, actor_id=seller.id, action="listing.delete", entity_type="listing", entity_id=listing_id
    )
    await db.commit()
    await stock.publish(str(listing_id), 0, ListingStatus.withdrawn.value)


# TODO(Role 3): POST /api/listings/{id}/image — upload to Supabase Storage, compress to
#   <=1600px WebP, save the public URL in listing.image_url (FR-USER-S-4, NFR-SYS-P-4).
# TODO(Role 3): GET /api/listings/{id}/reviews and the seller's average rating (FR-BUS-9).
# TODO(Role 3): POST/DELETE /api/listings/{id}/save — wishlist (FR-USER-B-8).


async def _own_listing(db: DB, listing_id: uuid.UUID, seller_id: uuid.UUID) -> Listing:
    listing = await get_listing_or_404(db, listing_id)
    if listing.seller_id != seller_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This listing no longer exists.")
    return listing

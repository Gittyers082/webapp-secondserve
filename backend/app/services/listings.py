"""Listing queries shared by routers."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Listing
from app.services.eligibility import listing_problems


async def get_listing_or_404(db: AsyncSession, listing_id: uuid.UUID) -> Listing:
    """Load a listing with its seller and shop name, ready for ListingOut."""
    result = await db.execute(
        select(Listing).where(Listing.id == listing_id).execution_options(populate_existing=True)
    )
    listing = result.unique().scalar_one_or_none()
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This listing no longer exists.")
    return listing


def ensure_eligible(listing: Listing) -> None:
    settings = get_settings()
    problems = listing_problems(
        original_price=listing.original_price,
        discounted_price=listing.discounted_price,
        quantity=max(listing.quantity_available, 1),
        expires_at=listing.expires_at,
        min_discount_percent=settings.min_discount_percent,
        max_discount_percent=settings.max_discount_percent,
    )
    if problems:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, problems)

"""The partner Surplus Board: who may buy, and telling partners about new surplus.

Shared by the seller's offer route (routers/partners.py) and the scheduled jobs
(services/jobs.py), so both announce surplus the same way.
"""

from datetime import timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import (
    AccountStatus,
    Listing,
    ListingChannel,
    ListingStatus,
    Role,
    SellerProfile,
    User,
)
from app.realtime.stock import stock
from app.services.notifications import notify

PHILIPPINE_TIME = timezone(timedelta(hours=8))  # no daylight saving, so a fixed offset is enough


def can_buy(partner: User) -> bool:
    """Only some partner types may buy partner offers (FR-USER-P-5). Donations are for all."""
    profile = partner.partner_profile
    return (
        profile is not None and profile.organization_type in get_settings().partner_buyer_type_list
    )


def ensure_can_buy(partner: User) -> None:
    if not can_buy(partner):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only LGUs and government agencies can buy partner offers. "
            "You can still claim free donations.",
        )


async def notify_partners(db: AsyncSession, listing: Listing) -> int:
    """Tell approved partners about new surplus. The caller commits.

    Donations go to every approved partner; paid offers only to partners who may buy them.
    Everyone is told, because the prototype serves one city (no location filter yet).
    """
    shop = await db.get(SellerProfile, listing.seller_id)
    shop_name = shop.business_name if shop else "A shop"
    expires = listing.expires_at.astimezone(PHILIPPINE_TIME).strftime("%b %d, %I:%M %p")
    donation = listing.channel == ListingChannel.donation

    if donation:
        title = "Free food available"
        body = (
            f"{shop_name} is giving away {listing.quantity_available} × {listing.name}. "
            f"Claim it before {expires}."
        )
    else:
        title = "New surplus offer"
        body = (
            f"{shop_name} has {listing.quantity_available} × {listing.name} at "
            f"₱{listing.discounted_price:,.2f} each. Available until {expires}."
        )

    partners = await db.scalars(
        select(User).where(User.role == Role.partner, User.status == AccountStatus.active)
    )
    count = 0
    for partner in partners.unique():
        if not donation and not can_buy(partner):
            continue
        notify(
            db,
            user_id=partner.id,
            type="surplus.donation" if donation else "surplus.offer",
            title=title,
            body=body,
            link="/partner/surplus",
        )
        count += 1
    return count


async def announce_left_marketplace(listing: Listing) -> None:
    """Tell open buyer pages to drop the listing. It's no longer on sale to them."""
    await stock.publish(str(listing.id), 0, ListingStatus.withdrawn.value)

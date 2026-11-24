"""Scheduled jobs, written as plain async functions.

They run from two places:
- POST /api/internal/run-jobs, called every 15 minutes by the "Scheduled jobs"
  GitHub Action. This is what runs on the free Render plan, which has no workers.
- The Celery tasks in workers/tasks.py, if Redis and a worker are ever added.

Each job takes a session, does its work, commits, and returns a small summary.
Every job must be safe to run twice in a row: the schedule can be late or repeat.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import (
    FulfillmentType,
    Listing,
    ListingChannel,
    ListingStatus,
    Notification,
    Order,
    OrderStatus,
    OrderType,
)
from app.realtime.stock import stock
from app.services import audit
from app.services import orders as order_service
from app.services.listings import lock_listings
from app.services.notifications import notify
from app.services.surplus import announce_left_marketplace, notify_partners

# Sellers hear about a listing this long before it expires (FR-USER-S-10c).
EXPIRY_WARNING = timedelta(hours=3)


def _manage_link(listing_id: object) -> str:
    return f"/seller/manage?listing={listing_id}"


async def expire_listings(db: AsyncSession) -> dict[str, Any]:
    """Mark listings past their expiry as expired, and warn sellers 3 hours ahead."""
    now = datetime.now(timezone.utc)

    expired = (
        await db.execute(
            update(Listing)
            .where(Listing.status == ListingStatus.active, Listing.expires_at <= now)
            .values(status=ListingStatus.expired)
            .returning(Listing.id, Listing.seller_id, Listing.name)
            .execution_options(synchronize_session=False)
        )
    ).all()
    for listing_id, seller_id, name in expired:
        notify(
            db,
            user_id=seller_id,
            type="listing.expired",
            title="A listing expired",
            body=f"{name} passed its expiry time and was taken off sale.",
            link=_manage_link(listing_id),
        )

    # Warn once per listing: a previous run may already have sent the warning.
    expiring = (
        await db.scalars(
            select(Listing).where(
                Listing.status == ListingStatus.active,
                Listing.expires_at > now,
                Listing.expires_at <= now + EXPIRY_WARNING,
                Listing.quantity_available > 0,
            )
        )
    ).unique()
    warned = 0
    for listing in expiring:
        link = _manage_link(listing.id)
        already = await db.scalar(
            select(Notification.id)
            .where(Notification.type == "listing.expiring", Notification.link == link)
            .limit(1)
        )
        if already is not None:
            continue
        notify(
            db,
            user_id=listing.seller_id,
            type="listing.expiring",
            title="A listing expires soon",
            body=(
                f"{listing.name} expires within 3 hours with {listing.quantity_available} "
                "left. Lower the price, or offer it to partners so it doesn't go to waste."
            ),
            link=link,
        )
        warned += 1

    await db.commit()
    for listing_id, _, _ in expired:
        await stock.publish(str(listing_id), 0, ListingStatus.expired.value)
    return {"expired": len(expired), "warned": warned}


async def escalate_surplus(db: AsyncSession) -> dict[str, Any]:
    """Move unsold food close to expiry to the partner Surplus Board (FR-SYS-14, FR-SYS-15).

    Listings within SURPLUS_WINDOW_HOURS of expiry that still have stock become partner
    offers at their current price (the seller can still lower it or make it a donation).
    """
    now = datetime.now(timezone.utc)
    due = (
        await db.scalars(
            select(Listing.id).where(
                Listing.status == ListingStatus.active,
                Listing.channel == ListingChannel.marketplace,
                Listing.quantity_available > 0,
                Listing.expires_at > now,
                Listing.expires_at <= now + timedelta(hours=get_settings().surplus_window_hours),
            )
        )
    ).all()

    moved: list[Listing] = []
    partners_told = 0
    if due:
        # Lock first, then look again: a buyer may have taken the last one meanwhile.
        for listing in (await lock_listings(db, list(due))).values():
            if (
                listing.status != ListingStatus.active
                or listing.channel != ListingChannel.marketplace
                or listing.quantity_available <= 0
                or listing.expires_at <= now
            ):
                continue
            listing.channel = ListingChannel.partner_offer
            listing.surplus_at = now
            notify(
                db,
                user_id=listing.seller_id,
                type="listing.surplus",
                title="Moved to the Surplus Board",
                body=(
                    f"{listing.name} is close to expiry, so it's now offered to partners. "
                    "You can lower the price or make it a donation."
                ),
                link=_manage_link(listing.id),
            )
            partners_told += await notify_partners(db, listing)
            audit.record(
                db,
                actor_id=None,
                action="listing.escalate",
                entity_type="listing",
                entity_id=listing.id,
            )
            moved.append(listing)

    await db.commit()
    for listing in moved:
        await announce_left_marketplace(listing)
    return {"escalated": len(moved), "partnersNotified": partners_told}


async def release_uncollected_claims(db: AsyncSession) -> dict[str, Any]:
    """Give stock back when a partner never collects (FR-USER-P-6).

    Pickup orders from partners (claims and purchases) still waiting after CLAIM_HOLD_HOURS
    are cancelled and their quantity goes back on the listing.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=get_settings().claim_hold_hours)
    stale = (
        await db.scalars(
            select(Order.id).where(
                Order.order_type != OrderType.sale,
                Order.fulfillment_type == FulfillmentType.pickup,
                Order.status.in_((OrderStatus.reserved, OrderStatus.ready)),
                Order.created_at <= cutoff,
            )
        )
    ).all()

    released = []
    for order_id in stale:
        listing = await order_service.release_claim(db, order_id)  # commits each one
        if listing is not None:
            released.append(listing)
    for listing in released:
        await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)
    return {"released": len(released)}


# Every job the runner calls, in order.
JOBS: dict[str, Callable[[AsyncSession], Awaitable[dict[str, Any]]]] = {
    "expire-listings": expire_listings,
    "escalate-surplus": escalate_surplus,
    "release-claims": release_uncollected_claims,
}


async def run_all(db: AsyncSession) -> dict[str, Any]:
    """Run every job. One job failing doesn't stop the others."""
    results: dict[str, Any] = {}
    for name, job in JOBS.items():
        try:
            results[name] = await job(db)
        except Exception as exc:  # noqa: BLE001 - report it and keep going
            await db.rollback()
            results[name] = {"error": type(exc).__name__}
    return results

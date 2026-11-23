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

from app.models import Listing, ListingStatus, Notification
from app.realtime.stock import stock
from app.services.notifications import notify

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


# Every job the runner calls, in order.
# TODO(Role 3): add escalate_surplus and releasing uncollected claims here.
JOBS: dict[str, Callable[[AsyncSession], Awaitable[dict[str, Any]]]] = {
    "expire-listings": expire_listings,
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

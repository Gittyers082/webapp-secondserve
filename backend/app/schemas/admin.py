"""Response shapes for the administrator screens."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models import Listing, Role
from app.schemas.common import Schema
from app.schemas.listing import ListingOut


class FlagIn(Schema):
    reason: str | None = Field(default=None, max_length=500)


class RemoveIn(Schema):
    reason: str | None = Field(default=None, max_length=500)


class ModeratedListingOut(ListingOut):
    """A listing as Item Moderation shows it: with why it was flagged."""

    flag_reason: str | None

    @classmethod
    def from_model(cls, listing: Listing) -> "ModeratedListingOut":
        return cls(
            **ListingOut.from_model(listing).model_dump(),
            flag_reason=listing.flag_reason,
        )


class SessionOut(Schema):
    """Someone who used the app recently (Active Sessions)."""

    user_id: UUID
    username: str
    role: Role
    last_seen_at: datetime


class StatsOut(Schema):
    """Platform totals for the admin dashboard and reports (FR-BUS-11, NFR-BUS-RA-1)."""

    users_by_role: dict[str, int]
    pending_accounts: int
    active_listings: int
    surplus_listings: int
    flagged_listings: int
    orders_by_status: dict[str, int]
    # Items in orders that were picked up or delivered: food that didn't go to waste.
    items_rescued: int
    items_donated: int
    items_distributed: int
    revenue: Decimal
    commission: Decimal
    customer_savings: Decimal
    average_discount_percent: int

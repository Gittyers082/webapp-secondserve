from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models import FoodCategory, Listing, ListingStatus
from app.schemas.common import Schema


class ListingCreate(Schema):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    category: FoodCategory
    original_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    discounted_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    quantity: int = Field(ge=1, le=10_000)
    expires_at: datetime
    # Defaults to the seller's business address when left out.
    pickup_location: str | None = Field(default=None, max_length=255)
    art: str | None = Field(default=None, max_length=40)


class ListingUpdate(Schema):
    """Everything optional: send only what changed (UC-04)."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, min_length=5, max_length=2000)
    category: FoodCategory | None = None
    original_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    discounted_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    quantity: int | None = Field(default=None, ge=0, le=10_000)
    expires_at: datetime | None = None
    pickup_location: str | None = Field(default=None, max_length=255)


class ListingStatusIn(Schema):
    status: Literal["active", "sold-out", "withdrawn"]


class ListingOut(Schema):
    id: UUID
    seller_id: UUID
    shop_name: str
    name: str
    description: str
    category: FoodCategory
    art: str | None
    image_url: str | None
    original_price: Decimal
    discounted_price: Decimal
    discount_percent: int
    quantity: int
    original_quantity: int
    expires_at: datetime
    pickup_location: str
    status: ListingStatus
    flagged: bool
    created_at: datetime

    @classmethod
    def from_model(cls, listing: Listing) -> "ListingOut":
        seller_profile = listing.seller.seller_profile if listing.seller else None
        return cls(
            id=listing.id,
            seller_id=listing.seller_id,
            shop_name=seller_profile.business_name if seller_profile else "",
            name=listing.name,
            description=listing.description,
            category=listing.category,
            art=listing.art,
            image_url=listing.image_url,
            original_price=listing.original_price,
            discounted_price=listing.discounted_price,
            discount_percent=discount_percent(listing.original_price, listing.discounted_price),
            quantity=listing.quantity_available,
            original_quantity=listing.original_quantity,
            expires_at=listing.expires_at,
            pickup_location=listing.pickup_location,
            status=listing.status,
            flagged=listing.flagged,
            created_at=listing.created_at,
        )


def discount_percent(original: Decimal, discounted: Decimal) -> int:
    """Same rounding as discountPercent() in src/data/types.ts."""
    if original <= 0:
        return 0
    return round((1 - discounted / original) * 100)


SortOption = Literal["newest", "price-asc", "price-desc", "discount", "expiring", "relevance"]

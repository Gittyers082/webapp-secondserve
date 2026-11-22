"""Product listings (ERD: Product Listing) and buyers' saved items."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import FoodCategory, FulfillmentOption, ListingKind, ListingStatus, str_enum
from app.models.user import User

Money = Numeric(10, 2)


class Listing(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "listings"
    __table_args__ = (
        # Eligibility rules enforced by the database as a last line of defence (FR-SYS-5).
        CheckConstraint("discounted_price < original_price", name="discount_below_original"),
        CheckConstraint("discounted_price >= 0", name="price_not_negative"),
        CheckConstraint("quantity_available >= 0", name="quantity_not_negative"),
        CheckConstraint("quantity_available <= original_quantity", name="quantity_within_original"),
        # Fuzzy search on the name (needs the pg_trgm extension, see the README).
        Index(
            "ix_listings_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_listings_status_expires", "status", "expires_at"),
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[FoodCategory] = mapped_column(str_enum(FoodCategory), index=True)

    original_price: Mapped[Decimal] = mapped_column(Money)
    discounted_price: Mapped[Decimal] = mapped_column(Money)

    quantity_available: Mapped[int] = mapped_column(Integer)
    original_quantity: Mapped[int] = mapped_column(Integer)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_location: Mapped[str] = mapped_column(String(255))

    image_url: Mapped[str | None] = mapped_column(String(500))
    # Key of a bundled illustration (FoodArt in types.ts) when there's no photo.
    art: Mapped[str | None] = mapped_column(String(40))

    status: Mapped[ListingStatus] = mapped_column(
        str_enum(ListingStatus), default=ListingStatus.active
    )
    fulfillment: Mapped[FulfillmentOption] = mapped_column(
        str_enum(FulfillmentOption), default=FulfillmentOption.pickup, server_default="pickup"
    )
    # Retail listings show in the marketplace; the other kinds show on the partner Surplus Board.
    kind: Mapped[ListingKind] = mapped_column(
        str_enum(ListingKind), default=ListingKind.retail, server_default="retail", index=True
    )
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str | None] = mapped_column(Text)

    seller: Mapped[User] = relationship(lazy="joined")


class SavedItem(Timestamps, Base):
    """Wishlist / compare list (FR-USER-B-8, B-9)."""

    __tablename__ = "saved_items"

    buyer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True
    )

"""Orders, simulated payments and reviews (ERD: Order, Payment Transaction, Review Rating).

An order is a reservation the customer collects, or has delivered (fulfillment_method).
For delivery orders, status "picked-up" means "delivered".
One order = one listing. Checking out a cart with three lines creates three orders.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import (
    DeliveryStatus,
    FulfillmentMethod,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    str_enum,
)
from app.models.listing import Listing, Money


class Order(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("total >= 0", name="total_not_negative"),
        CheckConstraint("delivery_fee >= 0", name="delivery_fee_not_negative"),
    )

    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)

    quantity: Mapped[int] = mapped_column(Integer)
    # Prices are copied at order time so later listing edits don't change past orders.
    unit_price: Mapped[Decimal] = mapped_column(Money)
    original_unit_price: Mapped[Decimal] = mapped_column(Money)
    total: Mapped[Decimal] = mapped_column(Money)

    # Short code the buyer shows at the counter (seller's /handover screen).
    # Delivery (FR-SYS-13). The fee is charged on top of `total` and earns no commission.
    fulfillment_method: Mapped[FulfillmentMethod] = mapped_column(
        str_enum(FulfillmentMethod), default=FulfillmentMethod.pickup, server_default="pickup"
    )
    delivery_address: Mapped[str | None] = mapped_column(String(255))
    delivery_fee: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), server_default="0")
    delivery_status: Mapped[DeliveryStatus | None] = mapped_column(str_enum(DeliveryStatus))
    delivery_reference: Mapped[str | None] = mapped_column(String(40))

    pickup_code: Mapped[str] = mapped_column(String(8), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus), default=OrderStatus.reserved, index=True
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    listing: Mapped[Listing] = relationship(lazy="joined")
    payment: Mapped["PaymentTransaction | None"] = relationship(
        back_populates="order", uselist=False, lazy="selectin"
    )


class PaymentTransaction(UUIDPrimaryKey, Timestamps, Base):
    """Simulated payment (FR-SYS-8). No card data is ever stored (NFR-SYS-S-5)."""

    __tablename__ = "payment_transactions"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Money)
    commission: Mapped[Decimal] = mapped_column(Money)  # platform fee (FR-BUS-4)
    method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod))
    status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus), default=PaymentStatus.pending
    )
    reference: Mapped[str] = mapped_column(String(40), unique=True)

    order: Mapped[Order] = relationship(back_populates="payment")


class Review(UUIDPrimaryKey, Timestamps, Base):
    """One review per picked-up order (FR-USER-B-15, FR-BUS-8/9)."""

    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_1_to_5"),)

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)

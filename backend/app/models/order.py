"""Orders, simulated payments and reviews (ERD: Order, Payment Transaction, Review Rating).

An order is collected at the store (pickup) or delivered through a partner courier
(delivery, simulated in the prototype). Buyers place sales; partners place partner
purchases and donation claims, so `buyer_id` holds whoever placed the order.
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
    DistributionStatus,
    FulfillmentType,
    OrderStatus,
    OrderType,
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
        # A delivery order must say where it goes (FR-USER-B-11).
        CheckConstraint(
            "fulfillment_type <> 'delivery' OR delivery_address IS NOT NULL",
            name="delivery_has_address",
        ),
        CheckConstraint(
            "delivery_fee IS NULL OR delivery_fee >= 0", name="delivery_fee_not_negative"
        ),
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
    pickup_code: Mapped[str] = mapped_column(String(8), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus), default=OrderStatus.reserved, index=True
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order_type: Mapped[OrderType] = mapped_column(
        str_enum(OrderType, length=24),
        default=OrderType.sale,
        server_default=OrderType.sale.value,
        index=True,
    )

    # Fulfillment (FR-SYS-13). Pickup orders leave the delivery fields empty.
    fulfillment_type: Mapped[FulfillmentType] = mapped_column(
        str_enum(FulfillmentType),
        default=FulfillmentType.pickup,
        server_default=FulfillmentType.pickup.value,
    )
    delivery_address: Mapped[str | None] = mapped_column(String(255))
    delivery_fee: Mapped[Decimal | None] = mapped_column(Money)
    delivery_status: Mapped[DeliveryStatus | None] = mapped_column(str_enum(DeliveryStatus))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Partner orders only: whether the items were passed on (FR-USER-P-9).
    distribution_status: Mapped[DistributionStatus | None] = mapped_column(
        str_enum(DistributionStatus)
    )
    distributed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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

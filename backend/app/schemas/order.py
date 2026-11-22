from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.models import (
    DeliveryStatus,
    FulfillmentMethod,
    ListingKind,
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.schemas.common import Schema


class OrderTerms(Schema):
    """How the customer pays and receives the order. Shared by single orders and carts."""

    payment_method: PaymentMethod = PaymentMethod.pay_on_pickup
    fulfillment: FulfillmentMethod = FulfillmentMethod.pickup
    delivery_address: str | None = Field(default=None, min_length=5, max_length=255)

    @model_validator(mode="after")
    def delivery_needs_address(self) -> "OrderTerms":
        if self.fulfillment == FulfillmentMethod.delivery and not self.delivery_address:
            raise ValueError("Add a delivery address.")
        return self


class OrderCreate(OrderTerms):
    listing_id: UUID
    quantity: int = Field(ge=1, le=100)


class CheckoutLine(Schema):
    listing_id: UUID
    quantity: int = Field(ge=1, le=100)


class CheckoutIn(OrderTerms):
    """A whole cart. Every line is reserved, or none are."""

    items: list[CheckoutLine] = Field(min_length=1, max_length=20)


class PickupIn(Schema):
    code: str = Field(min_length=4, max_length=8)


class DeliveryUpdateIn(Schema):
    status: Literal["out-for-delivery", "delivered"]


class OrderOut(Schema):
    id: UUID
    listing_id: UUID
    buyer_id: UUID
    seller_id: UUID
    food_name: str
    shop_name: str
    art: str | None
    image_url: str | None
    quantity: int
    unit_price: Decimal
    original_unit_price: Decimal
    total: Decimal
    delivery_fee: Decimal
    amount_due: Decimal  # total + delivery_fee
    kind: ListingKind
    fulfillment: FulfillmentMethod
    delivery_address: str | None
    delivery_status: DeliveryStatus | None
    delivery_reference: str | None
    pickup_location: str
    pickup_code: str
    expires_at: datetime
    status: OrderStatus
    payment_status: PaymentStatus | None
    picked_up_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, order: Order) -> "OrderOut":
        listing = order.listing
        seller_profile = listing.seller.seller_profile if listing.seller else None
        return cls(
            id=order.id,
            listing_id=order.listing_id,
            buyer_id=order.buyer_id,
            seller_id=order.seller_id,
            food_name=listing.name,
            shop_name=seller_profile.business_name if seller_profile else "",
            art=listing.art,
            image_url=listing.image_url,
            quantity=order.quantity,
            unit_price=order.unit_price,
            original_unit_price=order.original_unit_price,
            total=order.total,
            delivery_fee=order.delivery_fee,
            amount_due=order.total + order.delivery_fee,
            kind=listing.kind,
            fulfillment=order.fulfillment_method,
            delivery_address=order.delivery_address,
            delivery_status=order.delivery_status,
            delivery_reference=order.delivery_reference,
            pickup_location=listing.pickup_location,
            pickup_code=order.pickup_code,
            expires_at=listing.expires_at,
            status=order.status,
            payment_status=order.payment.status if order.payment else None,
            picked_up_at=order.picked_up_at,
            created_at=order.created_at,
        )

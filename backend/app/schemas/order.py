from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models import Order, OrderStatus, PaymentMethod, PaymentStatus
from app.schemas.common import Schema


class OrderCreate(Schema):
    listing_id: UUID
    quantity: int = Field(ge=1, le=100)
    payment_method: PaymentMethod = PaymentMethod.pay_on_pickup


class CheckoutLine(Schema):
    listing_id: UUID
    quantity: int = Field(ge=1, le=100)


class CheckoutIn(Schema):
    """A whole cart. Every line is reserved, or none are."""

    items: list[CheckoutLine] = Field(min_length=1, max_length=20)
    payment_method: PaymentMethod = PaymentMethod.pay_on_pickup


class PickupIn(Schema):
    code: str = Field(min_length=4, max_length=8)


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
            pickup_location=listing.pickup_location,
            pickup_code=order.pickup_code,
            expires_at=listing.expires_at,
            status=order.status,
            payment_status=order.payment.status if order.payment else None,
            picked_up_at=order.picked_up_at,
            created_at=order.created_at,
        )

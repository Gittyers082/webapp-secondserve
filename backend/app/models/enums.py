"""Status and type values shared by models, schemas and the frontend.

Keep these in sync with the unions in src/data/types.ts.
Stored as plain strings in Postgres (not native enums), so adding a value
later doesn't need a tricky migration.
"""

import enum

from sqlalchemy import Enum as SAEnum


class Role(str, enum.Enum):
    buyer = "buyer"
    seller = "seller"
    partner = "partner"  # LGU, government agency, charity or shelter (FR-USER-P-1)
    admin = "admin"


class AccountStatus(str, enum.Enum):
    pending = "pending"  # waiting for admin approval (sellers FR-BUS-7, partners FR-USER-P-2)
    active = "active"
    declined = "declined"
    banned = "banned"


class FoodCategory(str, enum.Enum):
    bread = "bread"
    pastries = "pastries"
    savory = "savory"
    cakes = "cakes"
    fruit_cups = "fruit-cups"
    groceries = "groceries"
    other = "other"


class ListingStatus(str, enum.Enum):
    active = "active"
    sold_out = "sold-out"
    withdrawn = "withdrawn"  # seller took it down (UC-05)
    expired = "expired"  # expiry passed
    removed = "removed"  # admin moderation


class OrderStatus(str, enum.Enum):
    reserved = "reserved"
    ready = "ready"
    picked_up = "picked-up"
    delivered = "delivered"  # delivery orders end here instead of picked-up
    cancelled = "cancelled"


class PaymentMethod(str, enum.Enum):
    pay_on_pickup = "pay-on-pickup"
    cash_on_delivery = "cash-on-delivery"
    gcash_simulated = "gcash-simulated"
    card_simulated = "card-simulated"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class FulfillmentType(str, enum.Enum):
    """How an order reaches the buyer or partner (FR-SYS-13)."""

    pickup = "pickup"
    delivery = "delivery"  # through a partner courier; simulated in the prototype


class DeliveryStatus(str, enum.Enum):
    """Progress of a delivery order (FR-USER-B-12). Pickup orders leave it empty."""

    pending = "pending"
    preparing = "preparing"
    out_for_delivery = "out-for-delivery"
    delivered = "delivered"
    cancelled = "cancelled"


class OrderType(str, enum.Enum):
    sale = "sale"  # a buyer's normal purchase
    partner_purchase = "partner-purchase"  # an agency buys surplus (FR-USER-P-5)
    donation = "donation"  # a charity claims a free item (FR-USER-P-6)


class ListingChannel(str, enum.Enum):
    """Who can see a listing (FR-SYS-14, FR-USER-S-13)."""

    marketplace = "marketplace"  # every buyer
    partner_offer = "partner-offer"  # partners only, at a further discount
    donation = "donation"  # partners only, free


class DistributionStatus(str, enum.Enum):
    """Whether a partner has passed received items on (FR-USER-P-9)."""

    pending = "pending"
    distributed = "distributed"


class Decision(str, enum.Enum):
    approved = "approved"
    declined = "declined"


def str_enum(enum_cls: type[enum.Enum], length: int = 20) -> SAEnum:
    """Column type that stores the enum's *value* (e.g. 'picked-up') as VARCHAR."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [m.value for m in cls],
        validate_strings=True,
    )

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
    admin = "admin"


class AccountStatus(str, enum.Enum):
    pending = "pending"  # waiting for admin approval (sellers, FR-BUS-7)
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
    cancelled = "cancelled"


class PaymentMethod(str, enum.Enum):
    pay_on_pickup = "pay-on-pickup"
    gcash_simulated = "gcash-simulated"
    card_simulated = "card-simulated"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


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

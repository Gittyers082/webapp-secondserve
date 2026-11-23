"""Buyer preferences: what the Shop shows first (NFR-USER-PERS-1, NFR-USER-PERS-2).

Stored in buyer_profiles.preferences (JSONB), so adding a field later needs no migration.
"""

from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.models import FoodCategory
from app.schemas.common import Schema


class Preferences(Schema):
    favourite_categories: list[FoodCategory] = Field(default_factory=list, max_length=7)
    min_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    max_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    # Only show listings the buyer can have delivered.
    delivery_only: bool = False

    @field_validator("favourite_categories")
    @classmethod
    def no_repeats(cls, value: list[FoodCategory]) -> list[FoodCategory]:
        return list(dict.fromkeys(value))  # keeps the buyer's order

    @model_validator(mode="after")
    def range_in_order(self) -> "Preferences":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("The lowest price can't be more than the highest price.")
        return self

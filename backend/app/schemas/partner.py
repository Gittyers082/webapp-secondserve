"""Request shapes for the partner Surplus Board (FR-USER-P-4 to P-9, FR-USER-S-13)."""

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import Schema
from app.schemas.order import Fulfillment


class PartnerOrderIn(Fulfillment):
    """An agency buying surplus, or a charity claiming a donation."""

    quantity: int = Field(ge=1, le=10_000)


class OfferToPartnersIn(Schema):
    """A seller moves an unsold listing to the Surplus Board (UC-13)."""

    channel: Literal["partner-offer", "donation"]
    # The further-discounted price for a partner offer. Donations are always free.
    partner_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def offer_needs_price(self) -> "OfferToPartnersIn":
        if self.channel == "partner-offer" and self.partner_price is None:
            raise ValueError("Set the partner price for a partner offer.")
        if self.channel == "donation" and self.partner_price not in (None, Decimal("0")):
            raise ValueError("Donations are free, so leave the price out.")
        return self

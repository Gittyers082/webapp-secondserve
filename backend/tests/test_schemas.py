import pytest
from pydantic import ValidationError

from app.schemas.listing import ConvertIn
from app.schemas.order import OrderCreate
from app.schemas.user import ProfileCreate

LISTING = "3f2c4f1e-7d5a-4c1b-9a53-0d6a2a1f0a11"


def test_delivery_orders_need_an_address():
    with pytest.raises(ValidationError):
        OrderCreate(listing_id=LISTING, quantity=1, fulfillment="delivery")
    order = OrderCreate(
        listing_id=LISTING, quantity=1, fulfillment="delivery", delivery_address="12 Session Rd"
    )
    assert order.delivery_address == "12 Session Rd"


def test_pickup_is_the_default():
    assert OrderCreate(listing_id=LISTING, quantity=1).fulfillment.value == "pickup"


def test_partner_offer_needs_a_price_and_donation_must_not_have_one():
    with pytest.raises(ValidationError):
        ConvertIn(kind="partner-offer")
    with pytest.raises(ValidationError):
        ConvertIn(kind="donation", partner_price=5)
    assert ConvertIn(kind="donation").partner_price is None


def test_partner_sign_up_needs_organization_details():
    base = {"role": "partner", "username": "foodbank1", "full_name": "Food Bank"}
    with pytest.raises(ValidationError):
        ProfileCreate(**base)
    details = {
        "organization_name": "Baguio Food Bank",
        "organization_type": "food-bank",
        "address": "Harrison Rd, Baguio",
        "contact_phone": "09171234567",
    }
    assert ProfileCreate(**base, partner=details).partner is not None

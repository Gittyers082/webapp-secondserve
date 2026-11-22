"""Validation rules for partners, delivery and the Surplus Board. No database needed."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models import FulfillmentType, Role
from app.schemas.listing import ListingCreate
from app.schemas.order import OrderCreate
from app.schemas.partner import OfferToPartnersIn, PartnerOrderIn
from app.schemas.user import ProfileCreate

PARTNER = {
    "organizationName": "Baguio City Social Welfare Office",
    "organizationType": "lgu",
    "contactPerson": "Ana Reyes",
    "address": "City Hall, Baguio City",
}


def listing(**overrides):
    values = {
        "name": "Ensaymada",
        "description": "Soft buttery bread",
        "category": "pastries",
        "originalPrice": "60",
        "discountedPrice": "30",
        "quantity": 5,
        "expiresAt": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
    }
    values.update(overrides)
    return values


def test_partner_is_a_role():
    assert Role("partner") is Role.partner


def test_partner_registration_needs_organization_details():
    with pytest.raises(ValidationError, match="organization details"):
        ProfileCreate(role="partner", username="cswdo", fullName="Ana Reyes")


def test_partner_registration_accepts_organization_details():
    profile = ProfileCreate(role="partner", username="cswdo", fullName="Ana Reyes", partner=PARTNER)
    assert profile.partner is not None
    assert profile.partner.organization_type == "lgu"


def test_nobody_registers_as_admin():
    with pytest.raises(ValidationError):
        ProfileCreate(role="admin", username="sneaky", fullName="Not Admin")


def test_delivery_order_needs_an_address():
    with pytest.raises(ValidationError, match="delivery address"):
        OrderCreate(listingId=uuid.uuid4(), quantity=1, fulfillmentType="delivery")


def test_pickup_is_the_default():
    order = OrderCreate(listingId=uuid.uuid4(), quantity=1)
    assert order.fulfillment_type is FulfillmentType.pickup
    assert order.delivery_address is None


def test_partner_order_reuses_the_fulfillment_rules():
    with pytest.raises(ValidationError, match="delivery address"):
        PartnerOrderIn(quantity=3, fulfillmentType="delivery")


def test_listing_must_offer_pickup_or_delivery():
    with pytest.raises(ValidationError, match="pickup, delivery, or both"):
        ListingCreate(**listing(allowsPickup=False, allowsDelivery=False))


def test_delivery_listing_needs_a_fee():
    with pytest.raises(ValidationError, match="delivery fee"):
        ListingCreate(**listing(allowsDelivery=True))
    ok = ListingCreate(**listing(allowsDelivery=True, deliveryFee="0"))
    assert ok.delivery_fee == Decimal("0")


def test_partner_offer_needs_a_price_and_donations_are_free():
    with pytest.raises(ValidationError, match="partner price"):
        OfferToPartnersIn(channel="partner-offer")
    with pytest.raises(ValidationError, match="free"):
        OfferToPartnersIn(channel="donation", partnerPrice="10")
    assert OfferToPartnersIn(channel="donation").partner_price is None


def test_partner_routes_require_login():
    client = TestClient(app)
    assert client.get("/api/partners/surplus").status_code == 401
    assert client.post(f"/api/partners/surplus/{uuid.uuid4()}/claim", json={}).status_code == 401

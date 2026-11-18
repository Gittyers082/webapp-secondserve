from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.eligibility import listing_problems

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def check(**overrides):
    values = dict(
        original_price=Decimal("120"),
        discounted_price=Decimal("60"),
        quantity=8,
        expires_at=NOW + timedelta(days=1),
        min_discount_percent=15,
        max_discount_percent=90,
        now=NOW,
    )
    values.update(overrides)
    return listing_problems(**values)


def test_valid_listing_has_no_problems():
    assert check() == []


def test_expired_listing_is_rejected():
    assert any("future" in p for p in check(expires_at=NOW - timedelta(minutes=1)))


def test_discount_must_be_lower_than_original():
    assert any("lower" in p for p in check(discounted_price=Decimal("120")))


def test_discount_too_small():
    # 10% off is below the 15% minimum
    assert any("at least 15%" in p for p in check(discounted_price=Decimal("108")))


def test_quantity_must_be_positive():
    assert any("Quantity" in p for p in check(quantity=0))


def test_naive_datetime_is_rejected():
    assert check(expires_at=datetime(2030, 1, 1)) == ["Expiry date must include a time zone."]

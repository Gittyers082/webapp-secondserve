"""Product eligibility rules (FR-SYS-5, FR-BUS-3, FR-BUS-6).

Pure functions with no database, so they're easy to unit test.
The database also enforces the price rule with a CHECK constraint.
"""

from datetime import datetime, timezone
from decimal import Decimal


def listing_problems(
    *,
    original_price: Decimal,
    discounted_price: Decimal,
    quantity: int,
    expires_at: datetime,
    min_discount_percent: int,
    max_discount_percent: int,
    now: datetime | None = None,
) -> list[str]:
    """Return a list of human-readable problems. Empty list = the listing is eligible."""
    now = now or datetime.now(timezone.utc)
    problems: list[str] = []

    if expires_at.tzinfo is None:
        problems.append("Expiry date must include a time zone.")
    elif expires_at <= now:
        problems.append("Expiry date must be in the future. Expired food can't be listed.")

    if quantity < 1:
        problems.append("Quantity must be at least 1.")

    if original_price <= 0:
        problems.append("Original price must be more than ₱0.")
    elif discounted_price >= original_price:
        problems.append("Discounted price must be lower than the original price.")
    else:
        percent = (1 - discounted_price / original_price) * 100
        if percent < min_discount_percent:
            problems.append(f"Discount must be at least {min_discount_percent}% off.")
        if percent > max_discount_percent:
            problems.append(f"Discount can't be more than {max_discount_percent}% off.")

    return problems

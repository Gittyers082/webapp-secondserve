"""Response shapes for the seller's Reviews and Analytics pages (FR-USER-S-9, FR-BUS-8)."""

from datetime import date
from decimal import Decimal

from app.schemas.common import Schema
from app.schemas.review import ReviewOut


class SellerReviewOut(ReviewOut):
    listing_name: str


class SellerReviewsOut(Schema):
    """Same top-level fields as a listing's reviews, plus the star counts."""

    items: list[SellerReviewOut]
    seller_average: float | None
    seller_review_count: int
    distribution: dict[int, int]  # stars (1 to 5) -> number of reviews


class SalesDay(Schema):
    date: date
    orders: int
    items_sold: int
    revenue: Decimal


class SalesOut(Schema):
    """Completed orders (picked up or delivered) in the last `days` days, Philippine time."""

    days: int
    orders: int
    items_sold: int  # sold to buyers and partners; donations are counted separately
    donated_items: int
    revenue: Decimal  # food only; delivery fees aren't the seller's sales
    commission: Decimal
    net_revenue: Decimal  # revenue minus commission
    discount_impact: Decimal  # what customers saved compared with the full price
    pending_orders: int  # reserved or ready right now, not limited to the period
    daily: list[SalesDay]  # one entry per day, oldest first, zeros included

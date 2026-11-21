from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import Schema


class ReviewCreate(Schema):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewOut(Schema):
    id: UUID
    order_id: UUID
    listing_id: UUID
    author: str
    rating: int
    comment: str | None
    created_at: datetime


class ReviewsOut(Schema):
    items: list[ReviewOut]
    seller_average: float | None
    seller_review_count: int

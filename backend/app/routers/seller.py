"""The seller's Reviews and Analytics pages. Owner: Role 3."""

from fastapi import APIRouter, Query

from app.core.deps import DB, ActiveSeller
from app.schemas.seller import SalesOut, SellerReviewsOut
from app.services import seller_stats

router = APIRouter(prefix="/api/seller", tags=["seller"])


@router.get("/reviews", response_model=SellerReviewsOut)
async def seller_reviews(
    db: DB,
    seller: ActiveSeller,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SellerReviewsOut:
    """Every review of this seller's food, newest first, with the average (FR-BUS-8)."""
    return await seller_stats.seller_reviews(db, seller.id, limit, offset)


@router.get("/sales", response_model=SalesOut)
async def seller_sales(
    db: DB,
    seller: ActiveSeller,
    days: int = Query(default=30, ge=1, le=365),
) -> SalesOut:
    """Items sold, revenue and discount impact over the last `days` days (FR-USER-S-9)."""
    return await seller_stats.sales_summary(db, seller.id, days)

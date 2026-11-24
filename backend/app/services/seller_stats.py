"""Numbers for the seller's Reviews and Analytics pages."""

import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Listing,
    Order,
    OrderStatus,
    OrderType,
    PaymentTransaction,
    Review,
    User,
)
from app.schemas.review import ReviewOut
from app.schemas.seller import SalesDay, SalesOut, SellerReviewOut, SellerReviewsOut
from app.services.surplus import PHILIPPINE_TIME

ZERO = Decimal("0.00")


async def seller_reviews(
    db: AsyncSession, seller_id: uuid.UUID, limit: int, offset: int
) -> SellerReviewsOut:
    rows = await db.execute(
        select(Review, User.username, Listing.name)
        .join(User, User.id == Review.buyer_id)
        .join(Listing, Listing.id == Review.listing_id)
        .where(Review.seller_id == seller_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [
        SellerReviewOut(
            **ReviewOut(
                id=review.id,
                order_id=review.order_id,
                listing_id=review.listing_id,
                author=username,
                rating=review.rating,
                comment=review.comment,
                created_at=review.created_at,
            ).model_dump(),
            listing_name=listing_name,
        )
        for review, username, listing_name in rows.all()
    ]

    counts = dict(
        (
            await db.execute(
                select(Review.rating, func.count(Review.id))
                .where(Review.seller_id == seller_id)
                .group_by(Review.rating)
            )
        ).all()
    )
    distribution = {stars: counts.get(stars, 0) for stars in range(1, 6)}
    total = sum(distribution.values())
    average = (
        round(sum(stars * n for stars, n in distribution.items()) / total, 1) if total else None
    )
    return SellerReviewsOut(
        items=items,
        seller_average=average,
        seller_review_count=total,
        distribution=distribution,
    )


async def sales_summary(db: AsyncSession, seller_id: uuid.UUID, days: int) -> SalesOut:
    today = datetime.now(PHILIPPINE_TIME).date()
    first = today - timedelta(days=days - 1)
    start = datetime.combine(first, time.min, tzinfo=PHILIPPINE_TIME)

    # An order counts on the day it was handed over.
    done_at = func.coalesce(Order.picked_up_at, Order.delivered_at, Order.created_at)
    day = cast(func.timezone("Asia/Manila", done_at), Date)
    sold = Order.order_type != OrderType.donation

    rows = await db.execute(
        select(
            day.label("day"),
            func.count(Order.id),
            func.coalesce(func.sum(case((sold, Order.quantity), else_=0)), 0),
            func.coalesce(func.sum(case((sold, 0), else_=Order.quantity)), 0),
            func.coalesce(func.sum(Order.total), 0),
            func.coalesce(func.sum(PaymentTransaction.commission), 0),
            func.coalesce(
                func.sum((Order.original_unit_price - Order.unit_price) * Order.quantity), 0
            ),
        )
        .select_from(Order)
        .outerjoin(PaymentTransaction, PaymentTransaction.order_id == Order.id)
        .where(
            Order.seller_id == seller_id,
            Order.status.in_((OrderStatus.picked_up, OrderStatus.delivered)),
            done_at >= start,
        )
        .group_by(day)
    )
    by_day: dict[date, tuple] = {row[0]: row[1:] for row in rows.all()}

    daily = []
    totals = [0, 0, 0, ZERO, ZERO, ZERO]
    for offset in range(days):
        d = first + timedelta(days=offset)
        orders, items, donated, revenue, commission, discount = by_day.get(
            d, (0, 0, 0, ZERO, ZERO, ZERO)
        )
        daily.append(SalesDay(date=d, orders=orders, items_sold=items, revenue=revenue))
        for i, value in enumerate((orders, items, donated, revenue, commission, discount)):
            totals[i] += value

    pending = await db.scalar(
        select(func.count(Order.id)).where(
            Order.seller_id == seller_id,
            Order.status.in_((OrderStatus.reserved, OrderStatus.ready)),
        )
    )
    orders, items, donated, revenue, commission, discount = totals
    return SalesOut(
        days=days,
        orders=orders,
        items_sold=items,
        donated_items=donated,
        revenue=revenue,
        commission=commission,
        net_revenue=revenue - commission,
        discount_impact=discount,
        pending_orders=pending or 0,
        daily=daily,
    )

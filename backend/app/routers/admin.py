"""Administrator screens (/admin/*). Owner: Role 1 (Project Lead)."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models import (
    AccountDecision,
    AccountStatus,
    Decision,
    DistributionStatus,
    Listing,
    ListingChannel,
    ListingStatus,
    Order,
    OrderStatus,
    OrderType,
    PaymentStatus,
    PaymentTransaction,
    Role,
    SellerProfile,
    User,
)
from app.realtime.stock import stock
from app.schemas.user import DecisionIn, DecisionOut, UserOut
from app.services.notifications import notify
from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from app.core.deps import DB, Admin
from app.schemas.admin import FlagIn, ModeratedListingOut, RemoveIn, SessionOut, StatsOut
from app.services import audit
from app.services.listings import get_listing_or_404

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: DB,
    admin: Admin,
    q: str | None = Query(default=None, max_length=100),
    role: Role | None = None,
    account_status: AccountStatus | None = Query(default=None, alias="status"),
) -> list[User]:
    """User Management screen: search, filter."""
    stmt = select(User).order_by(User.created_at.desc()).limit(200)
    if q:
        stmt = stmt.where(or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if role:
        stmt = stmt.where(User.role == role)
    if account_status:
        stmt = stmt.where(User.status == account_status)
    return list((await db.scalars(stmt)).all())


@router.post("/users/{user_id}/ban", response_model=UserOut)
async def ban(user_id: uuid.UUID, request: Request, db: DB, admin: Admin) -> User:
    return await _set_status(db, admin, user_id, AccountStatus.banned, "user.ban", request)


@router.post("/users/{user_id}/unban", response_model=UserOut)
async def unban(user_id: uuid.UUID, request: Request, db: DB, admin: Admin) -> User:
    return await _set_status(db, admin, user_id, AccountStatus.active, "user.unban", request)


@router.get("/approvals", response_model=list[UserOut])
async def pending_approvals(db: DB, admin: Admin) -> list[User]:
    """Pending Approvals screen: accounts waiting for verification (FR-BUS-7)."""
    stmt = select(User).where(User.status == AccountStatus.pending).order_by(User.created_at)
    return list((await db.scalars(stmt)).all())


@router.post("/approvals/{user_id}", response_model=UserOut)
async def decide(
    user_id: uuid.UUID, data: DecisionIn, request: Request, db: DB, admin: Admin
) -> User:
    user = await db.get(User, user_id)
    if user is None or user.status != AccountStatus.pending:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending account with that id.")

    approved = data.decision == Decision.approved
    user.status = AccountStatus.active if approved else AccountStatus.declined
    if approved and user.seller_profile is not None:
        user.seller_profile.verified_at = datetime.now(timezone.utc)
    if approved and user.partner_profile is not None:
        user.partner_profile.verified_at = datetime.now(timezone.utc)
    db.add(
        AccountDecision(
            user_id=user.id, admin_id=admin.id, decision=data.decision, reason=data.reason
        )
    )
    notify(
        db,
        user_id=user.id,
        type=f"account.{data.decision.value}",
        title="Your account was approved" if approved else "Your account was not approved",
        body="You can now start listing items."
        if approved
        else (data.reason or "Contact support."),
        email_to=user.email,
    )
    audit.record(
        db,
        actor_id=admin.id,
        action=f"user.{data.decision.value}",
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    await db.commit()
    await db.refresh(user, ["seller_profile", "partner_profile"])
    return user


@router.get("/decisions", response_model=list[DecisionOut])
async def decisions(db: DB, admin: Admin) -> list[DecisionOut]:
    """Approved/Declined Users screen."""
    rows = await db.execute(
        select(AccountDecision, User)
        .join(User, User.id == AccountDecision.user_id)
        .order_by(AccountDecision.created_at.desc())
        .limit(200)
    )
    return [
        DecisionOut(
            id=d.id,
            user_id=u.id,
            username=u.username,
            role=u.role,
            shop_name=u.seller_profile.business_name
            if u.seller_profile
            else u.partner_profile.organization_name
            if u.partner_profile
            else None,
            decision=d.decision,
            reason=d.reason,
            created_at=d.created_at,
        )
        for d, u in rows.unique().all()
    ]


# ---------------------------------------------------------------- Item Moderation


@router.get("/listings", response_model=list[ModeratedListingOut])
async def moderated_listings(
    db: DB,
    admin: Admin,
    flagged: bool | None = None,
    q: str | None = Query(default=None, max_length=100, description="Search name or shop"),
    listing_status: ListingStatus | None = Query(default=None, alias="status"),
) -> list[ModeratedListingOut]:
    """Item Moderation screen: every listing, flagged ones first (FR-BUS-8)."""
    stmt = (
        select(Listing)
        .join(SellerProfile, SellerProfile.user_id == Listing.seller_id)
        .order_by(Listing.flagged.desc(), Listing.created_at.desc())
        .limit(200)
    )
    if flagged is not None:
        stmt = stmt.where(Listing.flagged == flagged)
    if listing_status is not None:
        stmt = stmt.where(Listing.status == listing_status)
    if q:
        stmt = stmt.where(
            or_(
                Listing.name.icontains(q, autoescape=True),
                SellerProfile.business_name.icontains(q, autoescape=True),
            )
        )
    rows = await db.execute(stmt)
    return [ModeratedListingOut.from_model(listing) for listing in rows.unique().scalars()]


@router.post("/listings/{listing_id}/flag", response_model=ModeratedListingOut)
async def flag_listing(
    listing_id: uuid.UUID, request: Request, db: DB, admin: Admin, data: FlagIn | None = None
) -> ModeratedListingOut:
    """Mark a listing for review. It stays visible until it is removed."""
    listing = await get_listing_or_404(db, listing_id)
    listing.flagged = True
    listing.flag_reason = data.reason if data else None
    audit.record(
        db,
        actor_id=admin.id,
        action="listing.flag",
        entity_type="listing",
        entity_id=listing.id,
        details={"reason": listing.flag_reason},
        request=request,
    )
    await db.commit()
    return ModeratedListingOut.from_model(await get_listing_or_404(db, listing.id))


@router.post("/listings/{listing_id}/unflag", response_model=ModeratedListingOut)
async def unflag_listing(
    listing_id: uuid.UUID, request: Request, db: DB, admin: Admin
) -> ModeratedListingOut:
    """Clear a flag after review."""
    listing = await get_listing_or_404(db, listing_id)
    listing.flagged = False
    listing.flag_reason = None
    audit.record(
        db,
        actor_id=admin.id,
        action="listing.unflag",
        entity_type="listing",
        entity_id=listing.id,
        request=request,
    )
    await db.commit()
    return ModeratedListingOut.from_model(await get_listing_or_404(db, listing.id))


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_listing(
    listing_id: uuid.UUID, request: Request, db: DB, admin: Admin, data: RemoveIn | None = None
) -> None:
    """Take a listing out of the Shop and the Surplus Board (FR-BUS-8).

    It is not deleted: orders and reviews still point at it, and the seller can see why.
    Reservations already made are left for the seller to honour or cancel.
    """
    listing = await get_listing_or_404(db, listing_id)
    if listing.status == ListingStatus.removed:
        return
    listing.status = ListingStatus.removed
    reason = (data.reason if data else None) or listing.flag_reason
    notify(
        db,
        user_id=listing.seller_id,
        type="listing.removed",
        title="A listing was removed",
        body=f"An administrator removed {listing.name}." + (f" Reason: {reason}" if reason else ""),
        link="/seller/manage",
    )
    audit.record(
        db,
        actor_id=admin.id,
        action="listing.remove",
        entity_type="listing",
        entity_id=listing.id,
        details={"reason": reason},
        request=request,
    )
    await db.commit()
    await stock.publish(str(listing.id), listing.quantity_available, listing.status.value)


# ---------------------------------------------------------------- Active Sessions

_ONLINE_WINDOW = timedelta(minutes=30)


@router.get("/sessions", response_model=list[SessionOut])
async def active_sessions(db: DB, admin: Admin) -> list[SessionOut]:
    """Who used the app in the last 30 minutes, most recent first.

    Supabase holds the real sign-in sessions; this is based on users.last_seen_at,
    which every signed-in request refreshes (at most every 5 minutes).
    """
    since = datetime.now(timezone.utc) - _ONLINE_WINDOW
    users = await db.scalars(
        select(User)
        .where(User.last_seen_at >= since, User.status != AccountStatus.banned)
        .order_by(User.last_seen_at.desc())
        .limit(200)
    )
    return [
        SessionOut(
            user_id=user.id, username=user.username, role=user.role, last_seen_at=user.last_seen_at
        )
        for user in users
    ]


# ---------------------------------------------------------------- Stats


@router.get("/stats", response_model=StatsOut)
async def stats(db: DB, admin: Admin) -> StatsOut:
    """Platform totals (Objective 4, FR-BUS-11, NFR-BUS-RA-1)."""
    now = datetime.now(timezone.utc)
    zero = Decimal("0")

    users_by_role = {
        role.value: count
        for role, count in await db.execute(select(User.role, func.count()).group_by(User.role))
    }
    pending = await db.scalar(
        select(func.count()).select_from(User).where(User.status == AccountStatus.pending)
    )

    live = (Listing.status == ListingStatus.active, Listing.expires_at > now)
    active_listings = await db.scalar(
        select(func.count())
        .select_from(Listing)
        .where(*live, Listing.channel == ListingChannel.marketplace)
    )
    surplus_listings = await db.scalar(
        select(func.count())
        .select_from(Listing)
        .where(*live, Listing.channel != ListingChannel.marketplace)
    )
    flagged = await db.scalar(
        select(func.count())
        .select_from(Listing)
        .where(Listing.flagged.is_(True), Listing.status != ListingStatus.removed)
    )

    orders_by_status = {
        state.value: count
        for state, count in await db.execute(
            select(Order.status, func.count()).group_by(Order.status)
        )
    }

    received = Order.status.in_((OrderStatus.picked_up, OrderStatus.delivered))
    rescued, savings = (
        await db.execute(
            select(
                func.coalesce(func.sum(Order.quantity), 0),
                func.coalesce(
                    func.sum((Order.original_unit_price - Order.unit_price) * Order.quantity), zero
                ),
            ).where(received)
        )
    ).one()
    donated = await db.scalar(
        select(func.coalesce(func.sum(Order.quantity), 0)).where(
            received, Order.order_type == OrderType.donation
        )
    )
    distributed = await db.scalar(
        select(func.coalesce(func.sum(Order.quantity), 0)).where(
            Order.distribution_status == DistributionStatus.distributed
        )
    )
    revenue, commission = (
        await db.execute(
            select(
                func.coalesce(func.sum(PaymentTransaction.amount), zero),
                func.coalesce(func.sum(PaymentTransaction.commission), zero),
            ).where(PaymentTransaction.status == PaymentStatus.paid)
        )
    ).one()
    average_discount = await db.scalar(
        select(func.avg(1 - Listing.discounted_price / Listing.original_price) * 100).where(
            Listing.channel == ListingChannel.marketplace, Listing.original_price > 0
        )
    )

    return StatsOut(
        users_by_role=users_by_role,
        pending_accounts=pending or 0,
        active_listings=active_listings or 0,
        surplus_listings=surplus_listings or 0,
        flagged_listings=flagged or 0,
        orders_by_status=orders_by_status,
        items_rescued=int(rescued),
        items_donated=int(donated or 0),
        items_distributed=int(distributed or 0),
        revenue=revenue,
        commission=commission,
        customer_savings=savings,
        average_discount_percent=round(average_discount or 0),
    )


# TODO(Role 1): GET  /api/admin/export.csv — transaction export (NFR-BUS-RA-3).


async def _set_status(
    db: DB,
    admin: User,
    user_id: uuid.UUID,
    new_status: AccountStatus,
    action: str,
    request: Request,
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if user.role == Role.admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins can't be banned here.")
    user.status = new_status
    audit.record(
        db, actor_id=admin.id, action=action, entity_type="user", entity_id=user.id, request=request
    )
    await db.commit()
    await db.refresh(user, ["seller_profile"])
    return user

"""Administrator screens (/admin/*). Owner: Role 1 (Project Lead)."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import or_, select

from app.core.deps import DB, Admin
from app.models import AccountDecision, AccountStatus, Decision, Role, User
from app.schemas.user import DecisionIn, DecisionOut, UserOut
from app.services import audit
from app.services.notifications import notify

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
    await db.refresh(user, ["seller_profile"])
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
            shop_name=u.seller_profile.business_name if u.seller_profile else None,
            decision=d.decision,
            reason=d.reason,
            created_at=d.created_at,
        )
        for d, u in rows.unique().all()
    ]


# TODO(Role 1): GET  /api/admin/listings?flagged=true and POST /api/admin/listings/{id}/remove
#   (Item Moderation screen).
# TODO(Role 1): GET  /api/admin/sessions — who's online (use users.last_seen_at in the last 30 min).
# TODO(Role 1): GET  /api/admin/stats — users, listings, orders, avg discount, kg of food saved
#   (Objective 4, FR-BUS-11, NFR-BUS-RA-1).
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

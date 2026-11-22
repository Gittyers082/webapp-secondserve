"""The logged-in user's own account (UC-01, FR-USER-S-1/2, FR-USER-B-1/2).

Owner: Role 1 (Project Lead).

Sign-up flow:
1. Frontend calls supabase.auth.signUp({ email, password }). Supabase emails a
   verification link and hashes the password.
2. After the user logs in, the frontend calls POST /api/me/profile with the
   role and details. That creates our `users` row.
3. Every other call uses GET /api/me to find out who is logged in.
"""

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser, TokenUser
from app.core.rate_limit import limiter
from app.models import AccountStatus, BuyerProfile, PartnerProfile, Role, SellerProfile, User
from app.schemas.user import ProfileCreate, ProfileUpdate, UserOut
from app.services import audit

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
async def read_me(user: CurrentUser) -> User:
    return user


@router.post("/profile", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_profile(request: Request, data: ProfileCreate, claims: TokenUser, db: DB) -> User:
    if await db.get(User, claims.user_id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account is already set up.")
    if not claims.email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your login has no email address.")
    taken = await db.scalar(select(User.id).where(User.username == data.username))
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken.")

    role = Role(data.role)
    user = User(
        id=claims.user_id,
        email=claims.email,
        username=data.username,
        full_name=data.full_name,
        phone=data.phone,
        role=role,
        # Sellers and partners wait for an admin to verify them (FR-BUS-7, FR-USER-P-2).
        status=AccountStatus.pending
        if role in (Role.seller, Role.partner)
        else AccountStatus.active,
    )
    db.add(user)
    if role == Role.seller and data.seller:
        db.add(SellerProfile(user_id=user.id, **data.seller.model_dump()))
    elif role == Role.partner and data.partner:
        db.add(PartnerProfile(user_id=user.id, **data.partner.model_dump()))
    else:
        db.add(BuyerProfile(user_id=user.id, preferences={}))

    audit.record(
        db,
        actor_id=user.id,
        action="user.register",
        entity_type="user",
        entity_id=user.id,
        details={"role": role.value},
        request=request,
    )
    await db.commit()
    await db.refresh(user, ["seller_profile", "buyer_profile", "partner_profile"])
    return user


@router.patch("", response_model=UserOut)
async def update_me(data: ProfileUpdate, user: CurrentUser, db: DB) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    if data.seller is not None:
        if user.role != Role.seller or user.seller_profile is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only sellers have business details.")
        for field, value in data.seller.model_dump().items():
            setattr(user.seller_profile, field, value)
    if data.partner is not None:
        if user.role != Role.partner or user.partner_profile is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Only partners have organization details."
            )
        for field, value in data.partner.model_dump().items():
            setattr(user.partner_profile, field, value)
    await db.commit()
    await db.refresh(user, ["seller_profile", "partner_profile"])
    return user


# TODO(Role 1): POST /api/me/logo  — seller logo upload (NFR-USER-PERS-3)
# TODO(Role 1): GET/PUT /api/me/preferences — buyer favourite categories, price range (PERS-2)

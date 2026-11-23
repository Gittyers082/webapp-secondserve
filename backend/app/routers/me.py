"""The logged-in user's own account (UC-01, FR-USER-S-1/2, FR-USER-B-1/2).

Owner: Role 1 (Project Lead).

Sign-up flow:
1. Frontend calls supabase.auth.signUp({ email, password }). Supabase emails a
   verification link and hashes the password.
2. After the user logs in, the frontend calls POST /api/me/profile with the
   role and details. That creates our `users` row.
3. Every other call uses GET /api/me to find out who is logged in.
"""

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select

from app.core.deps import DB, ActiveBuyer, ActiveSeller, CurrentUser, TokenUser
from app.core.rate_limit import limiter
from app.models import (
    AccountStatus,
    BuyerProfile,
    Listing,
    ListingChannel,
    PartnerProfile,
    Role,
    SellerProfile,
    User,
)
from app.schemas.listing import ListingOut
from app.schemas.preferences import Preferences
from app.schemas.user import LogoOut, ProfileCreate, ProfileUpdate, UserOut
from app.services import audit, images
from app.services.search import listing_query

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


@router.post("/logo", response_model=LogoOut)
@limiter.limit("10/minute")
async def upload_logo(
    request: Request,
    db: DB,
    seller: ActiveSeller,
    file: UploadFile = File(...),
) -> LogoOut:
    """Upload the shop logo (JPEG, PNG or WebP, up to 2 MB), stored as a <=512px WebP.

    Buyers see it on the shop profile and listing cards (NFR-USER-PERS-3).
    """
    if seller.seller_profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Finish your shop details first.")
    if file.content_type not in images.ALLOWED_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Use a JPEG, PNG or WebP image."
        )
    raw = await file.read(_MAX_LOGO_BYTES + 1)
    if len(raw) > _MAX_LOGO_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Logos can be up to 2 MB.")

    seller.seller_profile.logo_url = await images.process_and_store_logo(seller.id, raw)
    audit.record(
        db,
        actor_id=seller.id,
        action="seller.logo",
        entity_type="user",
        entity_id=seller.id,
        request=request,
    )
    await db.commit()
    return LogoOut(logo_url=seller.seller_profile.logo_url)


_MAX_LOGO_BYTES = 2 * 1024 * 1024

# ---------------------------------------------------------------- Buyer preferences


async def _buyer_profile(db: DB, buyer: User) -> BuyerProfile:
    """The buyer's profile, created on first use for accounts made before it existed."""
    if buyer.buyer_profile is None:
        buyer.buyer_profile = BuyerProfile(user_id=buyer.id, preferences={})
        db.add(buyer.buyer_profile)
    return buyer.buyer_profile


def _read(profile: BuyerProfile) -> Preferences:
    # Unknown or outdated keys are ignored rather than failing the request.
    return Preferences.model_validate(
        {k: v for k, v in (profile.preferences or {}).items() if k in Preferences.model_fields}
    )


@router.get("/preferences", response_model=Preferences)
async def read_preferences(db: DB, buyer: ActiveBuyer) -> Preferences:
    """Favourite categories and price range (NFR-USER-PERS-2)."""
    return _read(await _buyer_profile(db, buyer))


@router.put("/preferences", response_model=Preferences)
async def save_preferences(data: Preferences, db: DB, buyer: ActiveBuyer) -> Preferences:
    profile = await _buyer_profile(db, buyer)
    # A new dict (not an in-place edit) so SQLAlchemy sees the JSONB change.
    profile.preferences = data.model_dump(mode="json")
    await db.commit()
    return data


@router.get("/recommendations", response_model=list[ListingOut])
async def recommendations(
    db: DB,
    buyer: ActiveBuyer,
    limit: int = Query(default=12, ge=1, le=50),
) -> list[ListingOut]:
    """The Shop's "Picked for you" row: marketplace listings that fit the buyer's
    preferences, soonest to expire first (NFR-USER-PERS-1). Without preferences
    this is simply what expires soonest."""
    prefs = _read(await _buyer_profile(db, buyer))
    stmt = listing_query(
        channels=(ListingChannel.marketplace,),
        min_price=prefs.min_price,
        max_price=prefs.max_price,
    )
    if prefs.favourite_categories:
        stmt = stmt.where(Listing.category.in_(prefs.favourite_categories))
    if prefs.delivery_only:
        stmt = stmt.where(Listing.allows_delivery.is_(True))
    rows = await db.execute(stmt.order_by(Listing.expires_at.asc()).limit(limit))
    return [ListingOut.from_model(listing) for listing in rows.unique().scalars()]

"""FastAPI dependencies: database session, current user, role guards.

Typical route:

    @router.post("/listings")
    async def create(data: ListingCreate, db: DB, seller: ActiveSeller): ...

- `DB`            an AsyncSession for this request
- `TokenUser`     the verified token claims (use only before the profile exists)
- `CurrentUser`   the logged-in user's row (401 if not logged in, 403 if banned/no profile)
- `ActiveSeller`  a seller whose account was approved (FR-BUS-7)
- `ActiveBuyer`   a buyer
- `ActivePartner` a partner whose account was approved (Surplus Board)
- `ActiveCustomer` a buyer or a partner (anyone who can place an order)
- `Admin`         an administrator
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidToken, TokenClaims, decode_access_token
from app.db.session import get_db
from app.models import AccountStatus, Role, User

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]


async def get_token_claims(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenClaims:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in first.")
    try:
        return decode_access_token(creds.credentials)
    except InvalidToken as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please log in again."
        ) from exc


TokenUser = Annotated[TokenClaims, Depends(get_token_claims)]


async def get_current_user(claims: TokenUser, db: DB) -> User:
    user = await db.get(User, claims.user_id)
    if user is None:
        # Logged in with Supabase but never finished POST /api/me/profile.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "profile_missing")
    if user.status == AccountStatus.banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been suspended.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role, must_be_active: bool = True):
    """Build a dependency that only lets the given roles through."""

    async def guard(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to this.")
        if must_be_active and user.status != AccountStatus.active:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Your account is still waiting for admin approval."
            )
        return user

    return guard


ActiveSeller = Annotated[User, Depends(require_role(Role.seller))]
ActiveBuyer = Annotated[User, Depends(require_role(Role.buyer))]
ActivePartner = Annotated[User, Depends(require_role(Role.partner))]
ActiveCustomer = Annotated[User, Depends(require_role(Role.buyer, Role.partner))]
Admin = Annotated[User, Depends(require_role(Role.admin))]

"""Verifies the access tokens Supabase Auth issues.

The frontend signs users up and in with supabase-js. Every API request then
carries `Authorization: Bearer <access_token>`, and this module checks that
token. We never see or store passwords; Supabase hashes them (NFR-SYS-S-1).

Two signing modes are supported:
- New Supabase projects sign tokens with asymmetric keys published at the
  project's JWKS URL. Used when SUPABASE_JWT_SECRET is empty.
- Older projects use a shared HS256 secret. Used when SUPABASE_JWT_SECRET is set.
"""

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt

from app.core.config import get_settings


class InvalidToken(Exception):
    """Raised when a token is missing, expired, or not signed by our Supabase project."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    email: str | None


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    # Caches the signing keys so we don't fetch them on every request.
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600)


def decode_access_token(token: str) -> TokenClaims:
    settings = get_settings()
    try:
        if settings.supabase_jwt_secret:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.jwt_audience,
            )
        else:
            signing_key = _jwks_client(settings.jwks_url).get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
            )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidToken("token has no valid subject") from exc

    return TokenClaims(user_id=user_id, email=payload.get("email"))

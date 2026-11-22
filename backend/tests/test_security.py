import time
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import InvalidToken, decode_access_token


def make_token(**overrides) -> str:
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "maria@example.com",
        "aud": "authenticated",
        "exp": int(time.time()) + 600,
    }
    payload.update(overrides)
    return jwt.encode(payload, get_settings().supabase_jwt_secret, algorithm="HS256")


def test_valid_token():
    user_id = uuid.uuid4()
    claims = decode_access_token(make_token(sub=str(user_id)))
    assert claims.user_id == user_id
    assert claims.email == "maria@example.com"


def test_expired_token():
    with pytest.raises(InvalidToken):
        decode_access_token(make_token(exp=int(time.time()) - 10))


def test_wrong_audience():
    with pytest.raises(InvalidToken):
        decode_access_token(make_token(aud="something-else"))


def test_bad_signature():
    token = jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated"}, "x" * 40, "HS256")
    with pytest.raises(InvalidToken):
        decode_access_token(token)

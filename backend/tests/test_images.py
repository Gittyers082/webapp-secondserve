import io

import pytest
from fastapi import HTTPException
from PIL import Image

from app.services.images import MAX_SIDE, compress


def png(width, height) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), "orange").save(out, "PNG")
    return out.getvalue()


def test_large_photo_is_shrunk_to_webp():
    result = Image.open(io.BytesIO(compress(png(4000, 3000))))
    assert result.format == "WEBP"
    assert max(result.size) == MAX_SIDE


def test_small_photo_is_not_enlarged():
    assert Image.open(io.BytesIO(compress(png(300, 200)))).size == (300, 200)


def test_non_image_is_rejected():
    with pytest.raises(HTTPException) as err:
        compress(b"not an image")
    assert err.value.status_code == 422

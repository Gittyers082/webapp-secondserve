"""Listing photos and shop logos: shrink to WebP, then store in Supabase Storage (NFR-SYS-P-4)."""

import asyncio
import io
import time
import uuid

import httpx
from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SIDE = 1600
LOGO_SIDE = 512
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def compress(data: bytes, max_side: int = MAX_SIDE) -> bytes:
    """Return the photo as a WebP no larger than `max_side` px on its longest side."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)  # respect the phone's rotation
            img.thumbnail((max_side, max_side))
            out = io.BytesIO()
            img.convert("RGB").save(out, "WEBP", quality=80, method=4)
            return out.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "That file isn't a usable image."
        ) from exc


async def store(listing_id: uuid.UUID, data: bytes) -> str:
    """Upload a listing photo to the public bucket and return its URL."""
    return await _upload(f"listings/{listing_id}.webp", data)


async def _upload(path: str, data: bytes) -> str:
    """Upload a WebP to `path` in the public bucket and return its URL."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Image storage isn't set up.")

    base = f"{settings.supabase_url.rstrip('/')}/storage/v1/object"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{base}/{settings.supabase_storage_bucket}/{path}",
                content=data,
                headers={
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                    "Content-Type": "image/webp",
                    "x-upsert": "true",  # replacing a photo reuses the same path
                },
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Couldn't save the photo. Try again."
        ) from exc

    # Same path every time, so add a version to get past browser and CDN caches.
    return f"{base}/public/{settings.supabase_storage_bucket}/{path}?v={int(time.time())}"


async def process_and_store(listing_id: uuid.UUID, raw: bytes) -> str:
    # Pillow is CPU-bound; run it off the event loop so other requests keep flowing.
    webp = await asyncio.to_thread(compress, raw)
    return await store(listing_id, webp)


async def process_and_store_logo(user_id: uuid.UUID, raw: bytes) -> str:
    """Shrink a shop logo to at most 512px and store it (NFR-USER-PERS-3)."""
    webp = await asyncio.to_thread(compress, raw, LOGO_SIDE)
    return await _upload(f"logos/{user_id}.webp", webp)

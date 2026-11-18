from fastapi import APIRouter
from sqlalchemy import text

from app.core.deps import DB

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Used by Render's health check. Doesn't touch the database."""
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(db: DB) -> dict[str, str]:
    await db.execute(text("select 1"))
    return {"status": "ok", "database": "reachable"}

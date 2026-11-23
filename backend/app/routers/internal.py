"""Endpoints for SecondServe's own automation, not for people. Owner: Role 1.

POST /api/internal/run-jobs runs the scheduled jobs (services/jobs.py). The
"Scheduled jobs" GitHub Action calls it every 15 minutes with the shared secret.
"""

import secrets
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import get_settings
from app.core.deps import DB
from app.core.rate_limit import limiter
from app.services import jobs

router = APIRouter(prefix="/api/internal", tags=["internal"], include_in_schema=False)


@router.post("/run-jobs")
@limiter.limit("6/minute")
async def run_jobs(
    request: Request,
    db: DB,
    x_jobs_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    secret = get_settings().jobs_secret
    # Same answer for "switched off", "no secret" and "wrong secret": nothing to probe.
    if not secret or not x_jobs_secret or not secrets.compare_digest(x_jobs_secret, secret):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
    return await jobs.run_all(db)

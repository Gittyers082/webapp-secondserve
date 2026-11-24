"""Background tasks. Owner: Role 1 (Project Lead)."""

import asyncio
import logging

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services import jobs
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(autoretry_for=(httpx.HTTPError,), retry_backoff=True, max_retries=3)
def send_email(to: str, subject: str, text: str) -> None:
    """Send one email through Resend (NFR-USER-R-2: within 60 seconds)."""
    settings = get_settings()
    if not settings.resend_api_key:
        log.warning("RESEND_API_KEY not set; not sending '%s' to %s", subject, to)
        return
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={"from": settings.email_from, "to": [to], "subject": subject, "text": text},
        timeout=10,
    )
    response.raise_for_status()


def _run(job) -> dict:
    """Run one async job from a synchronous Celery task, with its own engine.

    asyncio.run starts a new event loop each time, and a connection pool can't be
    shared between loops, so the engine is created and closed here.
    """

    async def main() -> dict:
        engine = create_async_engine(
            get_settings().database_url, connect_args={"statement_cache_size": 0}
        )
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                return await job(db)
        finally:
            await engine.dispose()

    return asyncio.run(main())


@celery_app.task
def expire_listings() -> None:
    """Every 10 minutes when Celery runs. On the free plan the GitHub Action runs it."""
    log.info("expire_listings: %s", _run(jobs.expire_listings))


@celery_app.task
def escalate_surplus() -> None:
    """Every 15 minutes: move unsold food to the partner Surplus Board (FR-SYS-14, FR-SYS-15)."""
    log.info("escalate_surplus: %s", _run(jobs.escalate_surplus))


@celery_app.task
def release_uncollected_claims() -> None:
    """Every 15 minutes: give stock back when a partner never collects (FR-USER-P-6)."""
    log.info("release_uncollected_claims: %s", _run(jobs.release_uncollected_claims))

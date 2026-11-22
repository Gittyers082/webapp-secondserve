"""Background tasks. Owner: Role 1 (Project Lead)."""

import logging

import httpx

from app.core.config import get_settings
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


@celery_app.task
def expire_listings() -> None:
    """Every 10 minutes.

    TODO(Role 1):
    - set status='expired' on active listings whose expires_at has passed
    - notify sellers about listings expiring in the next 3 hours (FR-USER-S-10c)
    Celery tasks are synchronous, so wrap async DB code with asyncio.run(...).
    """
    log.info("expire_listings: not implemented yet")


@celery_app.task
def escalate_surplus() -> None:
    """Every 15 minutes: move unsold food to the partner Surplus Board (FR-SYS-14, FR-SYS-15).

    TODO(Role 1):
    - find active marketplace listings that still have stock and expire within
      SURPLUS_WINDOW_HOURS (about 6 hours)
    - set `channel` to partner-offer, set `surplus_at`, and keep the price for now
      (the seller can still change it or turn it into a donation)
    - notify every approved partner in the seller's area, and tell the seller
    - publish the stock change so buyers' pages drop the item
    Celery tasks are synchronous, so wrap async DB code with asyncio.run(...).
    """
    log.info("escalate_surplus: not implemented yet")

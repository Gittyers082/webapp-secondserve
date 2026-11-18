"""Notifications (FR-SYS-10, UC-12).

Every notification is saved in-app first. If email is requested and Celery is
enabled, the email is queued in the background so the request isn't slowed down.
If email fails, the in-app record is still there (UC-12 exception flow).
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Notification

log = logging.getLogger(__name__)


def notify(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    link: str | None = None,
    email_to: str | None = None,
) -> Notification:
    """Add a notification to the current transaction. The caller commits."""
    notification = Notification(user_id=user_id, type=type, title=title, body=body, link=link)
    db.add(notification)

    if email_to:
        if get_settings().celery_enabled:
            # Imported here so the API doesn't need Celery installed to start.
            from app.workers.tasks import send_email

            send_email.delay(to=email_to, subject=title, text=body)
            notification.emailed = True
        else:
            log.info("CELERY_ENABLED is false; skipping email to %s (%s)", email_to, type)

    return notification

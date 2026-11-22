"""Celery app: background jobs through Upstash Redis.

Run a worker (with scheduled jobs) locally:
    celery -A app.workers.celery_app worker --beat --loglevel=info
"""

import ssl

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
broker = settings.redis_url or "memory://"

celery_app = Celery("secondserve", broker=broker, include=["app.workers.tasks"])
celery_app.conf.update(
    task_ignore_result=True,
    timezone="Asia/Manila",
    broker_connection_retry_on_startup=True,
    # Upstash uses rediss:// (TLS), and Celery wants the certificate policy spelled out.
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_REQUIRED}
    if broker.startswith("rediss://")
    else False,
    beat_schedule={
        "expire-listings": {
            "task": "app.workers.tasks.expire_listings",
            "schedule": crontab(minute="*/10"),
        },
    },
)

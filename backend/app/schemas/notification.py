from datetime import datetime
from uuid import UUID

from app.schemas.common import Schema


class NotificationOut(Schema):
    id: UUID
    type: str
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime

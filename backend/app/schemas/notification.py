from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_id: int
    actor_id: int | None = None
    actor_name: str | None = None
    company_id: int
    notification_type: str
    title: str
    message: str
    entity_type: str | None = None
    entity_id: int | None = None
    link_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    total_count: int


class MarkReadResponse(BaseModel):
    success: bool
    message: str
    unread_count: int

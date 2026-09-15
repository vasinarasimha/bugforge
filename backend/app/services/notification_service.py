import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    def create_notification(
        self,
        db: Session,
        recipient_id: int,
        company_id: int,
        notification_type: str,
        title: str,
        message: str,
        actor_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        link_url: str | None = None,
    ) -> Notification | None:
        """
        Create a persistent notification for a user.
        Deduplicates if an identical unread notification for the same entity was created recently (within 5 minutes).
        """
        # Deduplication check: same recipient, type, entity, within last 5 minutes
        recent_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        existing = (
            db.query(Notification)
            .filter(
                Notification.recipient_id == recipient_id,
                Notification.notification_type == notification_type,
                Notification.entity_type == entity_type,
                Notification.entity_id == entity_id,
                Notification.is_read == False,
                Notification.created_at >= recent_threshold,
            )
            .first()
        )
        if existing:
            # Already have an unread notification for this event recently
            return existing

        notif = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            company_id=company_id,
            notification_type=notification_type,
            title=title.strip()[:200],
            message=message.strip()[:500],
            entity_type=entity_type,
            entity_id=entity_id,
            link_url=link_url,
            is_read=False,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    def get_user_notifications(
        self,
        db: Session,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int, int]:
        """
        Retrieve notifications strictly for the authenticated user.
        Returns (serialized_items, unread_count, total_count).
        """
        base_query = db.query(Notification).filter(Notification.recipient_id == user_id)

        total_count = base_query.count()
        unread_count = (
            db.query(func.count(Notification.id))
            .filter(Notification.recipient_id == user_id, Notification.is_read == False)
            .scalar()
            or 0
        )

        query = base_query.options(joinedload(Notification.actor))
        if unread_only:
            query = query.filter(Notification.is_read == False)

        notifications = (
            query.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for n in notifications:
            items.append({
                "id": n.id,
                "recipient_id": n.recipient_id,
                "actor_id": n.actor_id,
                "actor_name": n.actor.full_name if n.actor else None,
                "company_id": n.company_id,
                "notification_type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "entity_type": n.entity_type,
                "entity_id": n.entity_id,
                "link_url": n.link_url,
                "is_read": n.is_read,
                "read_at": n.read_at,
                "created_at": n.created_at,
            })

        return items, unread_count, total_count

    def list_notifications(self, db: Session, user_id: int) -> list[Notification]:
        return db.query(Notification).filter(Notification.recipient_id == user_id).order_by(Notification.created_at.desc()).all()

    def get_unread_count(self, db: Session, user_id: int) -> int:
        return (
            db.query(func.count(Notification.id))
            .filter(Notification.recipient_id == user_id, Notification.is_read == False)
            .scalar()
            or 0
        )

    def mark_as_read(self, db: Session, notification_id: int, user_id: int) -> dict:
        """
        Mark a specific notification as read.
        Ensures the notification belongs to the authenticated user.
        """
        notif = (
            db.query(Notification)
            .options(joinedload(Notification.actor))
            .filter(Notification.id == notification_id)
            .first()
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        if notif.recipient_id != user_id:
            # Strictly forbidden to access or modify another user's notifications
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access notification belonging to another user",
            )

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notif)

        return {
            "id": notif.id,
            "recipient_id": notif.recipient_id,
            "actor_id": notif.actor_id,
            "actor_name": notif.actor.full_name if notif.actor else None,
            "company_id": notif.company_id,
            "notification_type": notif.notification_type,
            "title": notif.title,
            "message": notif.message,
            "entity_type": notif.entity_type,
            "entity_id": notif.entity_id,
            "link_url": notif.link_url,
            "is_read": notif.is_read,
            "read_at": notif.read_at,
            "created_at": notif.created_at,
        }

    def mark_all_as_read(self, db: Session, user_id: int) -> int:
        """
        Mark all unread notifications for the authenticated user as read.
        """
        now = datetime.now(timezone.utc)
        updated_count = (
            db.query(Notification)
            .filter(Notification.recipient_id == user_id, Notification.is_read == False)
            .update({"is_read": True, "read_at": now}, synchronize_session=False)
        )
        db.commit()
        return updated_count

    mark_all_read = mark_all_as_read

    def cleanup_read_notifications(
        self,
        db: Session,
        user_id: int | None = None,
        older_than_days: int = 1,
        company_id: int | None = None,
    ) -> int:
        """
        Delete read notifications (is_read == True) older than `older_than_days`.
        Strictly preserves all unread notifications (is_read == False).
        If user_id is provided, purges read notifications only for that user.
        If company_id is provided and user_id is None, purges for that company.
        If both are None, purges system-wide (for automated daily maintenance).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        query = db.query(Notification).filter(
            Notification.is_read == True,
            or_(
                Notification.read_at <= cutoff,
                and_(Notification.read_at == None, Notification.created_at <= cutoff),
            ),
        )
        if user_id is not None:
            query = query.filter(Notification.recipient_id == user_id)
        elif company_id is not None:
            query = query.filter(Notification.company_id == company_id)

        deleted_count = query.delete(synchronize_session=False)
        db.commit()
        logger.info(
            f"Notification cleanup: purged {deleted_count} read record(s) "
            f"(user_id={user_id}, company_id={company_id}, older_than_days={older_than_days})."
        )
        return deleted_count


notification_service = NotificationService()

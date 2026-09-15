from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    MarkReadResponse,
)
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_my_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    unread_only: bool = Query(default=False, description="Filter to only unread notifications"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Retrieve notifications strictly for the authenticated user.
    Never trusts frontend-supplied user IDs or tenant parameters.
    """
    items, unread_count, total_count = notification_service.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "unread_count": unread_count,
        "total_count": total_count,
    }


@router.get("/unread-count")
async def get_unread_notification_count(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Quick count of unread notifications for badge rendering.
    """
    count = notification_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Mark a specific notification as read.
    Forbidden if the notification belongs to another user.
    """
    return notification_service.mark_as_read(db, notification_id, current_user.id)


@router.post("/mark-all-read", response_model=MarkReadResponse)
async def mark_all_notifications_as_read(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Mark all unread notifications for the authenticated user as read.
    """
    updated_count = notification_service.mark_all_as_read(db, current_user.id)
    return {
        "success": True,
        "message": f"{updated_count} notification(s) marked as read.",
        "unread_count": 0,
    }


@router.delete("/read")
async def delete_read_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    older_than_days: int = Query(default=0, ge=0, description="Minimum age in days of read notifications to delete (0 = all read notifications)"),
):
    """
    Delete read notifications for the current authenticated user.
    Unread notifications are strictly preserved and never deleted.
    """
    deleted_count = notification_service.cleanup_read_notifications(
        db, user_id=current_user.id, older_than_days=older_than_days
    )
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"{deleted_count} read notification(s) deleted.",
    }


@router.post("/cleanup-daily")
async def trigger_daily_cleanup(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    older_than_days: int = Query(default=1, ge=0, description="Purge read notifications older than this many days (default 1 for daily purge)"),
):
    """
    Trigger daily system-wide cleanup of read notifications.
    Authorized for Admin and Super Admin roles.
    Unread notifications are strictly preserved across all tenants.
    """
    from fastapi import HTTPException
    user_roles = [r.name for r in current_user.roles]
    if "Super Admin" not in user_roles and "Admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Administrators can trigger notification cleanup",
        )

    is_super = "Super Admin" in user_roles
    company_id = None if is_super else current_user.company_id

    deleted_count = notification_service.cleanup_read_notifications(
        db, user_id=None, older_than_days=older_than_days, company_id=company_id
    )
    scope_desc = "across the platform" if is_super else "for your company"
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Daily cleanup complete: {deleted_count} read notification(s) deleted {scope_desc}.",
    }

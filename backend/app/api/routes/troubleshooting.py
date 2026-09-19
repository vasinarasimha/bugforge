"""
API routes for the AI-powered root-cause analysis troubleshooting engine.

All endpoints require authentication via get_current_user.
Session ownership is enforced at the service layer.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.troubleshooting import (
    TroubleshootingAnswerRequest,
    TroubleshootingConfirmRequest,
    TroubleshootingStartRequest,
)
from app.services.troubleshooting_service import troubleshooting_service

router = APIRouter(prefix="/troubleshooting")


@router.post("/start")
async def start_troubleshooting(
    req: TroubleshootingStartRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Start a new AI troubleshooting session.

    Takes the defect draft details and returns the session_id + first question.
    Restricted to Bug / Defect issue types.
    """
    if req.issue_id:
        from app.models.issue import Issue
        issue = db.query(Issue).filter(Issue.id == req.issue_id).first()
        if not issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
        defect_draft = {
            "title": req.title or issue.title,
            "description": req.description or issue.description,
            "project_id": req.project_id or issue.project_id,
            "priority_id": req.priority_id or issue.priority_id,
            "severity_id": req.severity_id or issue.severity_id,
            "status_id": req.status_id or issue.status_id,
            "issue_type": req.issue_type or issue.issue_type,
            "category_id": req.category_id or issue.category_id,
            "module_id": req.module_id or issue.module_id,
            "assigned_to": req.assigned_to or issue.assigned_to,
            "environment": req.environment or issue.environment,
            "browser": req.browser or issue.browser,
            "operating_system": req.operating_system or issue.operating_system,
            "reproduction_steps": req.reproduction_steps or issue.reproduction_steps,
            "expected_behavior": req.expected_behavior or issue.expected_behavior,
            "actual_behavior": req.actual_behavior or issue.actual_behavior,
        }
    else:
        if not req.title or not req.description or not req.project_id or not req.priority_id or not req.severity_id or not req.status_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: title, description, project_id, priority_id, severity_id, status_id"
            )
        defect_draft = req.model_dump()

    if defect_draft.get("issue_type") not in ("Bug", "Defect"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI Root-Cause Analysis is only available for Bug/Defect issue types. Got: '{defect_draft.get('issue_type')}'."
        )

    return troubleshooting_service.start_session(db, user, defect_draft)



@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: str,
    req: TroubleshootingAnswerRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Submit an answer to the current troubleshooting question.

    Returns either the next question, a confirmed root cause,
    or an insufficient evidence result.
    """
    return troubleshooting_service.submit_answer(
        db, user, session_id, req.question_number, req.answer
    )


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Get the current state of a troubleshooting session.
    """
    return troubleshooting_service.get_session(db, user, session_id)


@router.post("/{session_id}/confirm")
async def confirm_and_create(
    session_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    req: TroubleshootingConfirmRequest | None = None,
):
    """
    Confirm the troubleshooting result and create the actual issue.

    The issue is created from the original defect draft, with any optional
    overrides from the request body. The AI root cause is stored with the issue.
    """
    overrides = req.model_dump(exclude_unset=True) if req else None
    return troubleshooting_service.confirm_and_create(db, user, session_id, overrides)


@router.post("/{session_id}/cancel")
async def cancel_session(
    session_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Cancel a troubleshooting session without creating an issue.
    """
    troubleshooting_service.cancel_session(db, user, session_id)
    return {"status": "cancelled", "session_id": session_id}

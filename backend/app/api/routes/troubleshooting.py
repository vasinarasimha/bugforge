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
    if req.issue_type not in ("Bug", "Defect"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI Root-Cause Analysis is only available for Bug/Defect issue types. Got: '{req.issue_type}'."
        )
    defect_draft = req.model_dump()
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

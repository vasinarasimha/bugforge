import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.sprint import SprintStatus
from app.schemas.sprint import (
    SprintCreate, SprintUpdate, SprintResponse, SprintStatusResponse, SprintIssueAssign
)
from app.services.sprint_service import SprintService

router = APIRouter(prefix="/sprints", tags=["Sprints"])
service = SprintService()


def _serialize_issue(i):
    return {
        "id": i.id,
        "issue_key": i.issue_key,
        "title": i.title,
        "issue_type": i.issue_type,
        "status_name": i.status.name if i.status else "",
        "priority_name": i.priority.name if i.priority else "",
        "severity_name": i.severity.name if i.severity else "",
        "reporter_name": i.reporter.full_name if getattr(i, "reporter", None) else "",
        "assigned_to": i.assigned_to,
    }


def serialize(s):
    return {
        "id": s.id,
        "name": s.name,
        "goal": s.goal,
        "status_id": s.status_id,
        "status_name": s.status.name if s.status else "",
        "start_date": s.start_date,
        "end_date": s.end_date,
        "project_id": s.project_id,
        "project_name": s.project.name if getattr(s, "project", None) else "",
        "created_by": s.created_by,
        "creator_name": s.creator.full_name if getattr(s, "creator", None) else None,
        "created_at": s.created_at,
        "issue_count": len(s.issues) if s.issues else 0,
        "issues": [_serialize_issue(i) for i in (s.issues or [])],
    }


@router.get("/statuses", response_model=list[SprintStatusResponse])
async def list_sprint_statuses(db: Annotated[Session, Depends(get_db)]):
    return db.query(SprintStatus).filter(SprintStatus.is_active == True).all()


@router.get("", response_model=list[SprintResponse])
async def list_sprints(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = None,
):
    return [serialize(s) for s in service.list(db, project_id)]


@router.get("/{sprint_id}", response_model=SprintResponse)
async def get_sprint(
    sprint_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return serialize(service.get(db, sprint_id))


@router.post("", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
async def create_sprint(
    data: SprintCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    return serialize(service.create(db, data, user))


@router.put("/{sprint_id}", response_model=SprintResponse)
async def update_sprint(
    sprint_id: int,
    data: SprintUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return serialize(service.update(db, sprint_id, data))


@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sprint(
    sprint_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    service.delete(db, sprint_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{sprint_id}/issues/{issue_id}", status_code=status.HTTP_200_OK)
async def assign_issue_to_sprint(
    sprint_id: int,
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service.assign_issue(db, sprint_id, issue_id, user)
    return {"message": "Issue assigned to sprint"}


@router.delete("/{sprint_id}/issues/{issue_id}", status_code=status.HTTP_200_OK)
async def remove_issue_from_sprint(
    sprint_id: int,
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service.remove_issue(db, sprint_id, issue_id, user)
    return {"message": "Issue removed from sprint"}

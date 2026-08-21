from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_history import ProjectHistory
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])
service = ProjectService()

def serialize(p):
    return {
        "id": p.id,
        "name": p.name,
        "key": p.key,
        "description": p.description,
        "repository_url": p.repository_url,
        "status": p.status,
        "client_name": p.client_name,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "budget": p.budget,
        "tech_stack": p.tech_stack,
        "created_by": p.created_by,
        "creator_name": p.creator.full_name if p.creator else "",
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "is_active": p.is_active,
        "issue_count": len(p.issues),
        "project_manager_id": p.project_manager_id,
        "project_manager_name": p.project_manager.full_name if p.project_manager else "",
        "team_leader_id": p.team_leader_id,
        "team_leader_name": p.team_leader.full_name if p.team_leader else ""
    }

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    search: str | None = None,
    limit: int | None = 20,
    offset: int | None = 0
):
    # Apply record rules based on user role
    user_roles = [r.name for r in current_user.roles]

    if "Admin" in user_roles:
        # Admin sees all projects
        projects = service.list(db, search=search, limit=limit, offset=offset)
    elif "Project Manager" in user_roles:
        # Project Manager sees only their assigned projects
        projects = service.list_by_manager(db, current_user.id, search=search, limit=limit, offset=offset)
    elif "Team Leader" in user_roles:
        # Team Leader sees only their assigned projects
        projects = service.list_by_leader(db, current_user.id, search=search, limit=limit, offset=offset)
    else:
        # Others (Developer, QA, Reporter) see all active projects for context
        projects = service.list(db, search=search, limit=limit, offset=offset)

    return [serialize(p) for p in projects]

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    # Apply record rules for individual project access
    project = service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user_roles = [r.name for r in current_user.roles]

    # Check if user has access to this project
    has_access = False
    if "Admin" in user_roles:
        has_access = True
    elif "Project Manager" in user_roles and project.project_manager_id == current_user.id:
        has_access = True
    elif "Team Leader" in user_roles and project.team_leader_id == current_user.id:
        has_access = True
    elif "Developer" in user_roles or "QA" in user_roles or "Reporter" in user_roles:
        # These roles can see all projects for context (but may have limited issue visibility)
        has_access = True

    if not has_access:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    return serialize(project)

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    # Allow Admin and Project Manager to create projects
    user_roles = [r.name for r in user.roles]
    if not any(role in user_roles for role in ["Admin", "Project Manager"]):
        raise HTTPException(status_code=403, detail="Not authorized to create projects")

    # Set creator to current user
    return serialize(service.create(db, data, user))

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, data: ProjectUpdate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    # Only Admin and Project Manager can edit projects
    user_roles = [r.name for r in user.roles]
    if not any(role in user_roles for role in ["Admin", "Project Manager"]):
        raise HTTPException(status_code=403, detail="Not authorized to update projects")

    # Get the existing project to track changes
    existing_project = service.get(db, project_id)
    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update the project
    updated_project = service.update(db, project_id, data, user)

    # Record changes to ProjectHistory
    track_project_changes(db, existing_project, updated_project, user.id)

    return serialize(updated_project)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    # Only Admin can delete projects (according to requirements)
    user_roles = [r.name for r in user.roles]
    if "Admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Not authorized to delete projects")

    service.delete(db, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{project_id}/history", response_model=list[dict])
async def get_project_history(project_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    # Only Admin and Project Manager can view project history
    user_roles = [r.name for r in current_user.roles]
    if not any(role in user_roles for role in ["Admin", "Project Manager"]):
        raise HTTPException(status_code=403, detail="Not authorized to view project history")

    # Verify user has access to the project
    project = service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    has_access = False
    if "Admin" in user_roles:
        has_access = True
    elif "Project Manager" in user_roles and project.project_manager_id == current_user.id:
        has_access = True
    elif "Team Leader" in user_roles and project.team_leader_id == current_user.id:
        has_access = True

    if not has_access:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    # Get project history
    history_records = db.query(ProjectHistory).filter(ProjectHistory.project_id == project_id).order_by(ProjectHistory.created_at.desc()).all()

    return [
        {
            "id": h.id,
            "project_id": h.project_id,
            "user_id": h.user_id,
            "user_name": h.user.full_name if h.user else "System",
            "field_name": h.field_name,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "created_at": h.created_at
        }
        for h in history_records
    ]

def track_project_changes(db: Session, original: Project, updated: Project, user_id: int):
    """Track changes made to a project and record them in project_history"""
    # Define fields to track for changes
    tracked_fields = [
        "name", "key", "description", "repository_url", "status",
        "client_name", "start_date", "end_date", "budget", "tech_stack",
        "project_manager_id", "team_leader_id"
    ]

    for field in tracked_fields:
        old_value = getattr(original, field)
        new_value = getattr(updated, field)

        # Convert values to string for storage, handling None values
        old_str = str(old_value) if old_value is not None else None
        new_str = str(new_value) if new_value is not None else None

        # Only record if there's an actual change
        if old_str != new_str:
            history_record = ProjectHistory(
                project_id=updated.id,
                user_id=user_id,
                field_name=field,
                old_value=old_str,
                new_value=new_str
            )
            db.add(history_record)

    db.commit()

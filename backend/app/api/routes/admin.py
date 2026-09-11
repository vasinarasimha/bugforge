from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_role
from app.api.routes.issues import serialize as issue_serialize
from app.api.routes.projects import serialize as project_serialize
from app.core.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AdminUserCreate,
    AdminUserUpdate,
    RoleResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/admin", tags=["Admin"])
auth_service = AuthService()
user_repository = UserRepository()


@router.get("/stats")
async def admin_stats(
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    stmt = select(User).where(User.is_system_user == False)
    if current_admin.company_id:
        stmt = stmt.where(User.company_id == current_admin.company_id)
    users = list(db.scalars(stmt).all())
    issues = IssueService().list(db, company_id=current_admin.company_id)
    projects = ProjectService().list(db, company_id=current_admin.company_id)

    role_distribution = {role.value: 0 for role in UserRole}
    for u in users:
        primary_role = u.roles[0].name if getattr(u, "roles", None) else "Developer"
        role_distribution[primary_role] = role_distribution.get(primary_role, 0) + 1

    return {
        "total_users": len(users),
        "role_distribution": role_distribution,
        "total_projects": len(projects),
        "total_issues": len(issues),
        "open_issues": sum(1 for i in issues if i.status and i.status.name == "Open"),
        "in_progress_issues": sum(1 for i in issues if i.status and i.status.name == "In Progress"),
        "resolved_issues": sum(1 for i in issues if i.status and i.status.name == "Resolved"),
        "critical_issues": sum(1 for i in issues if i.priority and i.priority.name == "Critical"),
        "latest_projects": [project_serialize(p) for p in projects[:6]],
        "recent_issues": [issue_serialize(i) for i in issues[:8]],
    }


@router.get("/roles", response_model=list[RoleResponse])
def get_system_roles(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """List all valid system roles available for employee assignment."""
    roles = user_repository.get_all_roles(db)
    return roles


@router.get("/users")
def list_employees(
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List employees with searching (by name, email, department, location),
    filtering by role or active status, and pagination.
    """
    users, total = user_repository.list_employees(
        db=db,
        search=search,
        role_name=role,
        is_active=is_active,
        limit=limit,
        offset=offset,
        company_id=current_admin.company_id,
    )
    return {
        "data": [UserResponse.model_validate(u) for u in users],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/users/{user_id}", response_model=UserResponse)
def get_employee(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Get complete employee profile by ID (including inactive accounts)."""
    user = user_repository.get_by_id(db, user_id, include_inactive=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {user_id} not found.",
        )
    if current_admin.company_id and getattr(user, 'company_id', None) != current_admin.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access employee belonging to another company.",
        )
    return user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_data: AdminUserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Create a new employee account with role, contact, and address information."""
    return auth_service.create_employee(db, employee_data, current_admin=current_admin)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_employee(
    user_id: int,
    update_data: AdminUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """
    Update employee information (personal, contact, address, role, status, password reset).
    """
    return auth_service.update_user_admin(db, user_id, update_data, current_admin)


@router.delete("/users/{user_id}")
def deactivate_employee(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """
    Safely deactivate an employee account.
    Blocks login access while preserving defect history and audit logs.
    """
    user = auth_service.deactivate_user(db, user_id, current_admin)
    return {
        "message": f"Employee {user.full_name} deactivated successfully.",
        "user": UserResponse.model_validate(user),
    }

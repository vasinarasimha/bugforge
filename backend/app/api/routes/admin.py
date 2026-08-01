from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.routes.issues import serialize as issue_serialize
from app.api.routes.projects import serialize as project_serialize
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def admin_stats(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    users = list(db.scalars(select(User)).all())
    issues = IssueService().list(db)
    projects = ProjectService().list(db)

    role_distribution = {role.value: 0 for role in UserRole}
    for u in users:
        role_distribution[u.role.value] = role_distribution.get(u.role.value, 0) + 1

    return {
        "total_users": len(users),
        "role_distribution": role_distribution,
        "total_projects": len(projects),
        "total_issues": len(issues),
        "open_issues": sum(1 for i in issues if i.status == "Open"),
        "in_progress_issues": sum(1 for i in issues if i.status == "In Progress"),
        "resolved_issues": sum(1 for i in issues if i.status == "Resolved"),
        "critical_issues": sum(1 for i in issues if i.priority == "Critical"),
        "latest_projects": [project_serialize(p) for p in projects[:6]],
        "recent_issues": [issue_serialize(i) for i in issues[:8]],
    }

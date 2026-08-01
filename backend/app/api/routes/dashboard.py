from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.routes.issues import serialize as issue_serialize
from app.api.routes.projects import serialize as project_serialize
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardStatistics
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/statistics", response_model=DashboardStatistics)
async def statistics(db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    projects = ProjectService().list(db)
    issues = IssueService().list(db)
    return {"total_projects": len(projects), "total_reported_issues": len(issues), "total_in_progress": sum(i.status == "In Progress" for i in issues), "total_resolved": sum(i.status == "Resolved" for i in issues), "latest_projects": [project_serialize(p) for p in projects[:5]], "recent_issues": [issue_serialize(i) for i in issues[:5]]}

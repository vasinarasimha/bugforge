from pydantic import BaseModel

from app.schemas.issue import IssueResponse
from app.schemas.project import ProjectResponse


class DashboardStatistics(BaseModel):
    print('schemas/dashboard.py DashboardStatistics model initialized')
    total_projects: int
    total_reported_issues: int
    total_in_progress: int
    total_resolved: int
    latest_projects: list[ProjectResponse]
    recent_issues: list[IssueResponse]

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    KPISummary,
    SeverityDistribution,
    CategoryDistribution,
    StatusDistribution,
    DeveloperWorkload,
    DefectTrendPoint,
    ResolutionTimeMetrics,
    AnalyticsOverviewResponse
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])
service = AnalyticsService()

@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get complete analytics overview",
    description="Retrieve role-scoped defect metrics, KPIs, breakdowns, developer workloads, and trends aggregated from the database."
)
async def get_analytics_overview(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None, description="Optional: filter metrics by project ID"),
    team_id: Optional[int] = Query(default=None, description="Optional: filter metrics by team ID"),
    days: int = Query(default=30, ge=1, le=365, description="Time range for trend calculation (days)"),
):
    try:
        return service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=days)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to load analytics: {str(e)}"
        )

@router.get(
    "/kpis",
    response_model=KPISummary,
    summary="Get core defect KPIs",
    description="Get total, open, in-progress, resolved, closed, and average resolution time metrics."
)
async def get_kpis(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None, description="Optional project filter"),
    team_id: Optional[int] = Query(default=None, description="Optional team filter"),
):
    overview = service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=30)
    return overview.kpis

@router.get(
    "/severity",
    response_model=List[SeverityDistribution],
    summary="Get defect distribution by severity"
)
async def get_severity_distribution(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None),
    team_id: Optional[int] = Query(default=None),
):
    overview = service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=30)
    return overview.severity_distribution

@router.get(
    "/category",
    response_model=List[CategoryDistribution],
    summary="Get defect distribution by category"
)
async def get_category_distribution(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None),
    team_id: Optional[int] = Query(default=None),
):
    overview = service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=30)
    return overview.category_distribution

@router.get(
    "/status",
    response_model=List[StatusDistribution],
    summary="Get defect distribution by status"
)
async def get_status_distribution(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None),
    team_id: Optional[int] = Query(default=None),
):
    overview = service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=30)
    return overview.status_distribution

@router.get(
    "/developer-workload",
    response_model=List[DeveloperWorkload],
    summary="Get workload breakdown per developer"
)
async def get_developer_workload(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None),
    team_id: Optional[int] = Query(default=None),
):
    overview = service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=30)
    return overview.developer_workload

@router.get(
    "/trends",
    response_model=List[DefectTrendPoint],
    summary="Get time-series defect creation and resolution trends"
)
async def get_defect_trends(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None),
    team_id: Optional[int] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
):
    overview = service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=days)
    return overview.defect_trends

@router.get(
    "/resolution-time",
    response_model=ResolutionTimeMetrics,
    summary="Get detailed resolution time metrics"
)
async def get_resolution_time_metrics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[int] = Query(default=None),
    team_id: Optional[int] = Query(default=None),
):
    overview = service.get_overview(db, current_user, project_id=project_id, team_id=team_id, days=30)
    return overview.resolution_metrics

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.routes.issues import serialize as issue_serialize
from app.api.routes.projects import serialize as project_serialize
from app.core.database import get_db
from app.models.issue import Issue
from app.models.sprint import Sprint
from app.models.user import User
from app.models.history import IssueHistory
from app.repositories.user_repository import UserRepository
from app.schemas.dashboard import DashboardStatistics
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/statistics", response_model=DashboardStatistics)
async def statistics(db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    projects = ProjectService().list(db)
    issues = IssueService().list(db)
        # Recent history
    recent_history = db.query(IssueHistory).order_by(IssueHistory.created_at.desc()).limit(10).all()

    return {
        "total_projects": len(projects),
        "total_reported_issues": len(issues),
        "total_in_progress": sum(1 for i in issues if i.status.name == "In Progress"),
        "total_resolved": sum(1 for i in issues if i.status.name == "Resolved"),
        "latest_projects": [project_serialize(p) for p in projects[:5]],
        "recent_issues": [issue_serialize(i) for i in issues[:3]],
    }


@router.get("/pm-stats")
async def pm_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Project Manager stats — filtered to current PM's projects only."""
    # Check if user is Project Manager
    user_roles = [r.name for r in current_user.roles]
    if "Project Manager" not in user_roles:
        raise HTTPException(status_code=403, detail="Project Manager role required")

    # Get projects where user is the PM
    pm_projects = ProjectService().list_by_manager(db, current_user.id)
    pm_project_ids = [p.id for p in pm_projects]

    # Get issues for these projects only
    pm_issues = IssueService().list(db, project_ids=pm_project_ids)

    # Calculate stats
    active_projects = sum(1 for p in pm_projects if p.status == "Active")
    open_issues = sum(1 for i in pm_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in pm_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in pm_issues if i.status and i.status.name in ("Resolved", "Closed"))

    # Issues by priority
    issues_by_priority = defaultdict(int)
    for i in pm_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    # Issues by status
    issues_by_status = defaultdict(int)
    for i in pm_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    # Issues by type
    issues_by_type = defaultdict(int)
    for i in pm_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

    # Recent history
    recent_history_records = db.query(IssueHistory).join(Issue).filter(Issue.project_id.in_(pm_project_ids)).order_by(IssueHistory.created_at.desc()).limit(8).all()
    recent_history_serialized = [{"id": h.id, "field_name": h.field_name, "old_value": h.old_value, "new_value": h.new_value, "created_at": h.created_at.isoformat()} for h in recent_history_records]

    return {
        "total_projects": len(pm_projects),
        "total_issues": len(pm_issues),
        "active_projects": active_projects,
        "critical_open_issues": sum(1 for i in pm_issues if i.priority and i.priority.name in ["Critical", "High"] and i.status and i.status.name == "Open"),
        "active_sprints": [],
        "sprint_completion_rate": 0,
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_priority": dict(issues_by_priority),
        "issues_by_status": dict(issues_by_status),
        "issues_by_type": dict(issues_by_type),
        "projects": [{"id": p.id, "name": p.name, "key": p.key} for p in pm_projects[:10]],  # Recent projects
        "projects_with_metrics": [{"id": p.id, "name": p.name, "key": p.key, "progress": 0, "status": p.status} for p in pm_projects[:10]],
        "critical_issues": [issue_serialize(i) for i in pm_issues if i.priority and i.priority.name in ("Critical", "High") and i.status and i.status.name not in ("Resolved", "Closed") and i.assigned_to is None][:10],
        "recent_history": recent_history_serialized
    }


@router.get("/tl-stats")
async def tl_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Team Leader stats — filtered to current TL's projects only."""
    # Check if user is Team Leader
    user_roles = [r.name for r in current_user.roles]
    if "Team Leader" not in user_roles:
        raise HTTPException(status_code=403, detail="Team Leader role required")

    # Get projects where user is the TL
    tl_projects = ProjectService().list_by_leader(db, current_user.id)
    tl_project_ids = [p.id for p in tl_projects]

    # Get issues for these projects only
    tl_issues = IssueService().list(db, project_ids=tl_project_ids)

    # Calculate stats
    active_projects = sum(1 for p in tl_projects if p.status == "Active")
    open_issues = sum(1 for i in tl_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in tl_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in tl_issues if i.status and i.status.name in ("Resolved", "Closed"))

    # Issues by priority
    issues_by_priority = defaultdict(int)
    for i in tl_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    # Issues by status
    issues_by_status = defaultdict(int)
    for i in tl_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    # Issues by type
    issues_by_type = defaultdict(int)
    for i in tl_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

    # Recent history
    recent_history_records = db.query(IssueHistory).join(Issue).filter(Issue.project_id.in_(tl_project_ids)).order_by(IssueHistory.created_at.desc()).limit(8).all()
    recent_history_serialized = [{"id": h.id, "field_name": h.field_name, "old_value": h.old_value, "new_value": h.new_value, "created_at": h.created_at.isoformat()} for h in recent_history_records]

    return {
        "total_projects": len(tl_projects),
        "team_size": 0,
        "team_workload": [],
        "active_sprints": [],
        "active_projects": active_projects,
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_priority": dict(issues_by_priority),
        "issues_by_status": dict(issues_by_status),
        "issues_by_type": dict(issues_by_type),
        "projects": [{"id": p.id, "name": p.name, "key": p.key} for p in tl_projects[:10]],  # Recent projects
        "recent_issues": [issue_serialize(i) for i in tl_issues if i.assigned_to is None][:5]
    }


@router.get("/admin-stats")
async def admin_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Admin stats — full system-wide stats."""
    # Check if user is Admin
    user_roles = [r.name for r in current_user.roles]
    if "Admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin role required")

    # Get all projects and issues
    all_projects = ProjectService().list(db)
    all_issues = IssueService().list(db)

    # Calculate stats
    active_projects = sum(1 for p in all_projects if p.status == "Active")
    open_issues = sum(1 for i in all_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in all_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in all_issues if i.status and i.status.name in ("Resolved", "Closed"))

    # Issues by priority
    issues_by_priority = defaultdict(int)
    for i in all_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    # Issues by status
    issues_by_status = defaultdict(int)
    for i in all_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    # User stats by role
    user_repo = UserRepository()
    all_users = user_repo.list(db)
    users_by_role = defaultdict(int)
    for user in all_users:
        for role in user.roles:
            users_by_role[role.name] += 1

    return {
        "total_projects": len(all_projects),
        "active_projects": active_projects,
        "total_issues": len(all_issues),
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_priority": dict(issues_by_priority),
        "issues_by_status": dict(issues_by_status),
        "users_by_role": dict(users_by_role),
        "recent_projects": [{"id": p.id, "name": p.name, "key": p.key} for p in all_projects[:5]],
        "projects_with_metrics": [{"id": p.id, "name": p.name, "key": p.key, "progress": 0, "status": p.status} for p in all_projects[:10]],
        "recent_issues": [issue_serialize(i) for i in all_issues[:5]],
        "recent_history": []
    }


@router.get("/dev-stats")
async def dev_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Developer stats — issues assigned to current user."""
    # Check if user is Developer
    user_roles = [r.name for r in current_user.roles]
    if "Developer" not in user_roles:
        raise HTTPException(status_code=403, detail="Developer role required")

    # Get issues assigned to current user
    dev_issues = IssueService().list(db)
    dev_issues = [i for i in dev_issues if i.assigned_to == current_user.id]

    # Calculate stats
    open_issues = sum(1 for i in dev_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in dev_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in dev_issues if i.status and i.status.name in ("Resolved", "Closed"))

    # Issues by priority
    issues_by_priority = defaultdict(int)
    for i in dev_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    # Issues by status
    issues_by_status = defaultdict(int)
    for i in dev_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    # Issues by type
    issues_by_type = defaultdict(int)
    for i in dev_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

    # Recent history
    recent_history_records = db.query(IssueHistory).join(Issue).filter(Issue.assigned_to == current_user.id).order_by(IssueHistory.created_at.desc()).limit(8).all()
    recent_history_serialized = [{"id": h.id, "field_name": h.field_name, "old_value": h.old_value, "new_value": h.new_value, "created_at": h.created_at.isoformat()} for h in recent_history_records]

    return {
        "total_assigned": len(dev_issues),
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_priority": dict(issues_by_priority),
        "issues_by_status": dict(issues_by_status),
        "issues_by_type": dict(issues_by_type),
        "recent_issues": [issue_serialize(i) for i in dev_issues[:10]]
    }


@router.get("/qa-stats")
async def qa_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """QA stats — all issues, categorized by severity/status."""
    # Check if user is QA
    user_roles = [r.name for r in current_user.roles]
    if "QA" not in user_roles:
        raise HTTPException(status_code=403, detail="QA role required")

    # Get all issues
    all_issues = IssueService().list(db)

    # Calculate stats by severity
    issues_by_severity = defaultdict(int)
    for i in all_issues:
        issues_by_severity[i.severity.name if i.severity else "Unknown"] += 1

    # Issues by status
    issues_by_status = defaultdict(int)
    for i in all_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    # Issues by type
    issues_by_type = defaultdict(int)
    for i in all_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

    # Open/critical issues that need attention
    open_issues = sum(1 for i in all_issues if i.status and i.status.name == "Open")
    critical_issues = sum(1 for i in all_issues if i.severity and i.severity.name == "Critical" and i.status and i.status.name not in ("Resolved", "Closed"))

    return {
        "total_issues": len(all_issues),
        "open_issues": open_issues,
        "critical_issues": critical_issues,
        "issues_by_severity": dict(issues_by_severity),
        "issues_by_status": dict(issues_by_status),
        "issues_by_type": dict(issues_by_type),
        "recent_issues": [issue_serialize(i) for i in all_issues[:10]]
    }


@router.get("/reporter-stats")
async def reporter_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Reporter stats — current user's own reported issues only."""
    # Check if user is Reporter
    user_roles = [r.name for r in current_user.roles]
    if "Reporter" not in user_roles:
        raise HTTPException(status_code=403, detail="Reporter role required")

    # Get issues reported by current user
    reporter_issues = IssueService().list(db, reporter_id=current_user.id)

    # Calculate stats
    open_issues = sum(1 for i in reporter_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in reporter_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in reporter_issues if i.status and i.status.name in ("Resolved", "Closed"))

    # Issues by status
    issues_by_status = defaultdict(int)
    for i in reporter_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    # Issues by priority
    issues_by_priority = defaultdict(int)
    for i in reporter_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    return {
        "total_reported": len(reporter_issues),
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_status": dict(issues_by_status),
        "issues_by_priority": dict(issues_by_priority),
        "recent_reports": [issue_serialize(i) for i in reporter_issues[:10]]
    }
# trigger reload


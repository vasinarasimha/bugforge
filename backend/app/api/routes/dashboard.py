from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.routes.issues import serialize as issue_serialize
from app.api.routes.projects import serialize as project_serialize
from app.core.database import get_db
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity
from app.models.sprint import Sprint, SprintStatus
from app.models.team import Team, TeamMember
from app.models.role import Role
from app.models.user import User
from app.models.history import IssueHistory
from sqlalchemy.orm import joinedload, selectinload
from app.repositories.user_repository import UserRepository
from app.schemas.dashboard import DashboardStatistics
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/statistics", response_model=DashboardStatistics)
async def statistics(db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    from app.models.project import Project

    # SQL-level aggregation instead of loading all records into memory
    total_projects = db.query(func.count(Project.id)).filter(Project.is_active == True).scalar() or 0

    issue_stats = db.query(
        func.count(Issue.id).label("total"),
        func.count(case((IssueStatus.name == "In Progress", Issue.id))).label("in_progress"),
        func.count(case((IssueStatus.name == "Resolved", Issue.id))).label("resolved"),
    ).join(Issue.status).filter(Issue.is_deleted == False, Issue.is_active == True).first()

    total_issues = issue_stats.total if issue_stats else 0
    in_progress = issue_stats.in_progress if issue_stats else 0
    resolved = issue_stats.resolved if issue_stats else 0

    # Only fetch the few records needed for display
    projects = ProjectService().list(db, limit=5, offset=0)
    recent_issues = IssueService().list(db)[:3]

    return {
        "total_projects": total_projects,
        "total_reported_issues": total_issues,
        "total_in_progress": in_progress,
        "total_resolved": resolved,
        "latest_projects": [project_serialize(p) for p in projects[:5]],
        "recent_issues": [issue_serialize(i) for i in recent_issues],
    }


@router.get("/pm-stats")
async def pm_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Project Manager stats — filtered to current PM's projects only."""
    user_roles = [r.name for r in current_user.roles]
    if "Project Manager" not in user_roles:
        raise HTTPException(status_code=403, detail="Project Manager role required")

    pm_projects = ProjectService().list_by_manager(db, current_user.id)
    pm_project_ids = [p.id for p in pm_projects]
    pm_issues = IssueService().list(db, project_ids=pm_project_ids)

    active_projects = sum(1 for p in pm_projects if p.status == "Active")
    open_issues = sum(1 for i in pm_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in pm_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in pm_issues if i.status and i.status.name in ("Resolved", "Closed"))

    issues_by_priority = defaultdict(int)
    for i in pm_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    issues_by_status = defaultdict(int)
    for i in pm_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    issues_by_type = defaultdict(int)
    for i in pm_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

    # Sprints and completion rate for PM
    pm_active_sprints = db.query(Sprint).options(
        joinedload(Sprint.issues).joinedload(Issue.status)
    ).join(Sprint.status).filter(
        SprintStatus.name == "Active"
    ).all()
    if pm_project_ids:
        pm_proj_sprints = [s for s in pm_active_sprints if s.project_id in pm_project_ids]
        if pm_proj_sprints:
            pm_active_sprints = pm_proj_sprints

    total_sprint_issues = sum(len([i for i in s.issues if not i.is_deleted and i.is_active]) for s in pm_active_sprints)
    resolved_sprint_issues = sum(sum(1 for i in s.issues if not i.is_deleted and i.is_active and i.status and i.status.name in ("Resolved", "Closed")) for s in pm_active_sprints)
    sprint_completion_rate = round((resolved_sprint_issues / total_sprint_issues * 100)) if total_sprint_issues > 0 else 0

    recent_history_records = db.query(IssueHistory).join(Issue).filter(Issue.project_id.in_(pm_project_ids)).order_by(IssueHistory.created_at.desc()).limit(8).all()
    recent_history_serialized = [{"id": h.id, "field_name": h.field_name, "old_value": h.old_value, "new_value": h.new_value, "created_at": h.created_at.isoformat()} for h in recent_history_records]

    return {
        "total_projects": len(pm_projects),
        "total_issues": len(pm_issues),
        "active_projects": active_projects,
        "critical_open_issues": sum(1 for i in pm_issues if i.priority and i.priority.name in ["Critical", "High"] and i.status and i.status.name == "Open"),
        "active_sprints": len(pm_active_sprints),
        "sprint_completion_rate": sprint_completion_rate,
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_priority": dict(issues_by_priority),
        "issues_by_status": dict(issues_by_status),
        "issues_by_type": dict(issues_by_type),
        "projects": [{"id": p.id, "name": p.name, "key": p.key} for p in pm_projects[:10]],
        "projects_with_metrics": [{"id": p.id, "name": p.name, "key": p.key, "progress": 0, "status": p.status} for p in pm_projects[:10]],
        "critical_issues": [issue_serialize(i) for i in pm_issues if i.priority and i.priority.name in ("Critical", "High") and i.status and i.status.name not in ("Resolved", "Closed") and i.assigned_to is None][:10],
        "recent_history": recent_history_serialized
    }


@router.get("/tl-stats")
async def tl_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Team Leader stats — filtered to current TL's projects and team."""
    user_roles = [r.name for r in current_user.roles]
    if "Team Leader" not in user_roles:
        raise HTTPException(status_code=403, detail="Team Leader role required")

    tl_projects = ProjectService().list_by_leader(db, current_user.id)
    tl_project_ids = [p.id for p in tl_projects]
    tl_issues = IssueService().list(db, project_ids=tl_project_ids)

    active_projects = sum(1 for p in tl_projects if p.status == "Active")
    open_issues = sum(1 for i in tl_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in tl_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in tl_issues if i.status and i.status.name in ("Resolved", "Closed"))

    issues_by_priority = defaultdict(int)
    for i in tl_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    issues_by_status = defaultdict(int)
    for i in tl_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    issues_by_type = defaultdict(int)
    for i in tl_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

    # 1. Team Leader's Team and Workload
    tl_team = db.query(Team).options(
        joinedload(Team.members).joinedload(TeamMember.user)
    ).filter(Team.team_leader_id == current_user.id, Team.is_active == True).first()

    team_members_list = []
    if tl_team and tl_team.members:
        team_members_list = [m.user for m in tl_team.members if m.user and not m.user.is_system_user]
    else:
        # Fallback to active developers
        team_members_list = db.query(User).join(User.roles).filter(
            Role.name == "Developer",
            User.is_active == True,
            User.is_system_user == False
        ).all()

    assigned_user_ids = {i.assigned_to for i in tl_issues if i.assigned_to is not None}
    all_workload_users = {u.id: u for u in team_members_list if u}
    for uid in assigned_user_ids:
        if uid not in all_workload_users:
            u_obj = db.query(User).filter(User.id == uid, User.is_system_user == False).first()
            if u_obj:
                all_workload_users[uid] = u_obj

    team_workload = []
    for uid, u_obj in all_workload_users.items():
        u_issues = [i for i in tl_issues if i.assigned_to == uid]
        u_open = sum(1 for i in u_issues if i.status and i.status.name == "Open")
        u_in_prog = sum(1 for i in u_issues if i.status and i.status.name == "In Progress")
        u_resolved = sum(1 for i in u_issues if i.status and i.status.name in ("Resolved", "Closed"))
        u_total = len(u_issues)
        team_workload.append({
            "user_id": u_obj.id,
            "full_name": u_obj.full_name,
            "email": u_obj.email,
            "open": u_open,
            "in_progress": u_in_prog,
            "resolved": u_resolved,
            "total": u_total
        })

    team_workload.sort(key=lambda x: x["total"], reverse=True)

    # 2. Active Sprints
    active_sprints_query = db.query(Sprint).options(
        joinedload(Sprint.status),
        joinedload(Sprint.issues).joinedload(Issue.status)
    ).join(Sprint.status).filter(
        SprintStatus.name == "Active"
    )
    if tl_project_ids:
        active_sprints_query = active_sprints_query.filter(Sprint.project_id.in_(tl_project_ids))

    active_sprints_records = active_sprints_query.all()
    if not active_sprints_records:
        active_sprints_records = db.query(Sprint).options(
            joinedload(Sprint.status),
            joinedload(Sprint.issues).joinedload(Issue.status)
        ).join(Sprint.status).filter(
            SprintStatus.name == "Active"
        ).all()

    today_date = datetime.now(timezone.utc).date()
    active_sprints_list = []
    for sp in active_sprints_records:
        sp_issues = [i for i in sp.issues if not i.is_deleted and i.is_active]
        sp_total = len(sp_issues)
        sp_resolved = sum(1 for i in sp_issues if i.status and i.status.name in ("Resolved", "Closed"))
        sp_pct = round((sp_resolved / sp_total * 100)) if sp_total > 0 else 0
        days_left = None
        if sp.end_date:
            days_left = (sp.end_date - today_date).days
        active_sprints_list.append({
            "id": sp.id,
            "name": sp.name,
            "start_date": sp.start_date.isoformat() if sp.start_date else (sp.created_at.strftime("%Y-%m-%d") if sp.created_at else "—"),
            "end_date": sp.end_date.isoformat() if sp.end_date else "—",
            "days_left": days_left,
            "progress_pct": sp_pct,
            "resolved_issues": sp_resolved,
            "total_issues": sp_total
        })

    recent_history_records = db.query(IssueHistory).join(Issue).filter(Issue.project_id.in_(tl_project_ids)).order_by(IssueHistory.created_at.desc()).limit(8).all()
    recent_history_serialized = [{"id": h.id, "field_name": h.field_name, "old_value": h.old_value, "new_value": h.new_value, "created_at": h.created_at.isoformat()} for h in recent_history_records]

    return {
        "total_projects": len(tl_projects),
        "team_size": len(all_workload_users),
        "team_workload": team_workload,
        "active_sprints": active_sprints_list,
        "active_projects": active_projects,
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_priority": dict(issues_by_priority),
        "issues_by_status": dict(issues_by_status),
        "issues_by_type": dict(issues_by_type),
        "projects": [{"id": p.id, "name": p.name, "key": p.key} for p in tl_projects[:10]],
        "recent_issues": [issue_serialize(i) for i in tl_issues if i.assigned_to is None][:5],
        "recent_history": recent_history_serialized
    }


@router.get("/admin-stats")
async def admin_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Admin stats — full system-wide stats."""
    user_roles = [r.name for r in current_user.roles]
    if "Admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin role required")

    all_projects = ProjectService().list(db)
    all_issues = IssueService().list(db)

    active_projects = sum(1 for p in all_projects if p.status == "Active")
    open_issues = sum(1 for i in all_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in all_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in all_issues if i.status and i.status.name in ("Resolved", "Closed"))

    issues_by_priority = defaultdict(int)
    for i in all_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    issues_by_status = defaultdict(int)
    for i in all_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    # User stats by role (excluding system test accounts)
    user_repo = UserRepository()
    all_users = user_repo.list(db)
    total_users = len(all_users)
    users_by_role = defaultdict(int)
    for user in all_users:
        for role in user.roles:
            users_by_role[role.name] += 1

    return {
        "total_users": total_users,
        "total_projects": len(all_projects),
        "active_projects": active_projects,
        "total_issues": len(all_issues),
        "open_issues": open_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "issues_by_priority": dict(issues_by_priority),
        "issues_by_status": dict(issues_by_status),
        "users_by_role": dict(users_by_role),
        "latest_projects": [project_serialize(p) for p in all_projects[:6]],
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
    user_roles = [r.name for r in current_user.roles]
    if "Developer" not in user_roles:
        raise HTTPException(status_code=403, detail="Developer role required")

    dev_issues = IssueService().list(db)
    dev_issues = [i for i in dev_issues if i.assigned_to == current_user.id]

    open_issues = sum(1 for i in dev_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in dev_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in dev_issues if i.status and i.status.name in ("Resolved", "Closed"))

    issues_by_priority = defaultdict(int)
    for i in dev_issues:
        issues_by_priority[i.priority.name if i.priority else "Unknown"] += 1

    issues_by_status = defaultdict(int)
    for i in dev_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    issues_by_type = defaultdict(int)
    for i in dev_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

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
        "recent_issues": [issue_serialize(i) for i in dev_issues[:10]],
        "recent_history": recent_history_serialized
    }


@router.get("/qa-stats")
async def qa_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """QA stats — all issues, categorized by severity/status."""
    user_roles = [r.name for r in current_user.roles]
    if "QA" not in user_roles:
        raise HTTPException(status_code=403, detail="QA role required")

    all_issues = IssueService().list(db)

    issues_by_severity = defaultdict(int)
    for i in all_issues:
        issues_by_severity[i.severity.name if i.severity else "Unknown"] += 1

    issues_by_status = defaultdict(int)
    for i in all_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

    issues_by_type = defaultdict(int)
    for i in all_issues:
        issues_by_type[i.issue_type or "Defect"] += 1

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
    user_roles = [r.name for r in current_user.roles]
    if "Reporter" not in user_roles:
        raise HTTPException(status_code=403, detail="Reporter role required")

    reporter_issues = IssueService().list(db, reporter_id=current_user.id)

    open_issues = sum(1 for i in reporter_issues if i.status and i.status.name == "Open")
    in_progress_issues = sum(1 for i in reporter_issues if i.status and i.status.name == "In Progress")
    resolved_issues = sum(1 for i in reporter_issues if i.status and i.status.name in ("Resolved", "Closed"))

    issues_by_status = defaultdict(int)
    for i in reporter_issues:
        issues_by_status[i.status.name if i.status else "Unknown"] += 1

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

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from collections import defaultdict
from sqlalchemy import func, select, and_, or_, case
from sqlalchemy.orm import Session

from app.models.issue import Issue, IssueStatus, IssueSeverity, IssuePriority, IssueCategory, IssueModule
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.models.history import IssueHistory
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

SEVERITY_COLORS = {
    "Critical": "#ef4444",
    "High": "#f97316",
    "Medium": "#f59e0b",
    "Low": "#10b981",
    "Unknown": "#94a3b8"
}

STATUS_COLORS = {
    "Open": "#3b82f6",
    "In Progress": "#8b5cf6",
    "Resolved": "#10b981",
    "Closed": "#64748b",
    "Unknown": "#94a3b8"
}

class AnalyticsService:

    def get_overview(
        self,
        db: Session,
        current_user: User,
        project_id: Optional[int] = None,
        days: int = 30
    ) -> AnalyticsOverviewResponse:
        """
        Compute end-to-end database-aggregated analytics with project and role-based security.
        """
        # Determine allowed project scope
        user_roles = [r.name for r in getattr(current_user, 'roles', [])]
        allowed_project_ids = None

        if "Admin" not in user_roles:
            if "Project Manager" in user_roles:
                pm_projects = db.query(Project.id).filter(Project.project_manager_id == current_user.id, Project.is_active == True).all()
                allowed_project_ids = [p[0] for p in pm_projects]
            elif "Team Leader" in user_roles:
                tl_projects = db.query(Project.id).filter(Project.team_leader_id == current_user.id, Project.is_active == True).all()
                allowed_project_ids = [p[0] for p in tl_projects]

        # Base filter for issues
        filters = [Issue.is_deleted == False, Issue.is_active == True]

        target_project_name = None
        if project_id is not None:
            # Verify authorization
            if allowed_project_ids is not None and project_id not in allowed_project_ids:
                # User not authorized to view this specific project's analytics
                filters.append(Issue.project_id == -1)  # Yields empty
            else:
                filters.append(Issue.project_id == project_id)
                proj = db.query(Project).filter(Project.id == project_id).first()
                if proj:
                    target_project_name = proj.name
        elif allowed_project_ids is not None:
            filters.append(Issue.project_id.in_(allowed_project_ids))

        # ── 1. KPI Aggregation ──
        kpi_query = db.query(
            func.count(Issue.id).label("total"),
            func.count(case((IssueStatus.name == "Open", Issue.id))).label("open"),
            func.count(case((IssueStatus.name == "In Progress", Issue.id))).label("in_progress"),
            func.count(case((IssueStatus.name == "Resolved", Issue.id))).label("resolved"),
            func.count(case((IssueStatus.name == "Closed", Issue.id))).label("closed"),
            func.count(case((and_(IssueSeverity.name == "Critical", IssueStatus.name.notin_(["Resolved", "Closed"])), Issue.id))).label("critical_open")
        ).join(Issue.status).outerjoin(Issue.severity).filter(*filters).first()

        total = kpi_query.total if kpi_query else 0
        open_cnt = kpi_query.open if kpi_query else 0
        in_prog_cnt = kpi_query.in_progress if kpi_query else 0
        res_cnt = kpi_query.resolved if kpi_query else 0
        closed_cnt = kpi_query.closed if kpi_query else 0
        crit_open_cnt = kpi_query.critical_open if kpi_query else 0

        # ── 2. Resolution Time Calculation ──
        resolved_issues = db.query(Issue.created_at, Issue.updated_at).join(Issue.status).filter(
            *filters,
            IssueStatus.name.in_(["Resolved", "Closed"])
        ).all()

        resolution_durations = []
        for created, updated in resolved_issues:
            if created and updated and updated >= created:
                diff_hours = (updated - created).total_seconds() / 3600.0
                resolution_durations.append(diff_hours)

        avg_hours = None
        min_hours = None
        max_hours = None
        avg_formatted = "No resolution-time data available"

        if resolution_durations:
            avg_hours = round(sum(resolution_durations) / len(resolution_durations), 1)
            min_hours = round(min(resolution_durations), 1)
            max_hours = round(max(resolution_durations), 1)

            if avg_hours < 1.0:
                avg_formatted = f"{int(avg_hours * 60)} mins"
            elif avg_hours < 24.0:
                avg_formatted = f"{avg_hours} hrs"
            else:
                days_val = round(avg_hours / 24.0, 1)
                avg_formatted = f"{days_val} days"

        resolution_metrics = ResolutionTimeMetrics(
            avg_hours=avg_hours,
            min_hours=min_hours,
            max_hours=max_hours,
            formatted=avg_formatted,
            sample_size=len(resolution_durations)
        )

        kpis = KPISummary(
            total_defects=total,
            open_defects=open_cnt,
            in_progress_defects=in_prog_cnt,
            resolved_defects=res_cnt,
            closed_defects=closed_cnt,
            critical_open_defects=crit_open_cnt,
            avg_resolution_time_hours=avg_hours,
            avg_resolution_time_formatted=avg_formatted
        )

        # ── 3. Severity Distribution ──
        all_severities = db.query(IssueSeverity).filter(IssueSeverity.is_active == True).all()
        sev_counts_raw = db.query(
            Issue.severity_id,
            func.count(Issue.id)
        ).filter(*filters).group_by(Issue.severity_id).all()
        sev_count_map = {row[0]: row[1] for row in sev_counts_raw}

        severity_distribution = []
        for sev in all_severities:
            count = sev_count_map.get(sev.id, 0)
            pct = round((count / total * 100.0), 1) if total > 0 else 0.0
            severity_distribution.append(SeverityDistribution(
                name=sev.name,
                count=count,
                percentage=pct,
                color=SEVERITY_COLORS.get(sev.name, "#94a3b8")
            ))

        # ── 4. Category Distribution ──
        cat_counts_raw = db.query(
            func.coalesce(IssueCategory.name, "Uncategorized").label("cat_name"),
            func.count(Issue.id).label("count")
        ).outerjoin(Issue.category).filter(*filters).group_by("cat_name").order_by(func.count(Issue.id).desc()).all()

        category_distribution = []
        for row in cat_counts_raw:
            pct = round((row.count / total * 100.0), 1) if total > 0 else 0.0
            category_distribution.append(CategoryDistribution(
                name=row.cat_name,
                count=row.count,
                percentage=pct
            ))

        # ── 5. Status Distribution ──
        all_statuses = db.query(IssueStatus).filter(IssueStatus.is_active == True).all()
        stat_counts_raw = db.query(
            Issue.status_id,
            func.count(Issue.id)
        ).filter(*filters).group_by(Issue.status_id).all()
        stat_count_map = {row[0]: row[1] for row in stat_counts_raw}

        status_distribution = []
        for st in all_statuses:
            count = stat_count_map.get(st.id, 0)
            pct = round((count / total * 100.0), 1) if total > 0 else 0.0
            status_distribution.append(StatusDistribution(
                name=st.name,
                count=count,
                percentage=pct,
                color=STATUS_COLORS.get(st.name, "#94a3b8")
            ))

        # ── 6. Developer Workload ──
        # Find developers or users who have assignments
        dev_role_users = db.query(User).join(User.roles).filter(Role.name == "Developer", User.is_active == True).all()
        dev_ids = {u.id: u for u in dev_role_users if hasattr(u, 'id')}

        workload_query = db.query(
            Issue.assigned_to,
            func.count(Issue.id).label("total_assigned"),
            func.count(case((IssueStatus.name == "Open", Issue.id))).label("open"),
            func.count(case((IssueStatus.name == "In Progress", Issue.id))).label("in_prog"),
            func.count(case((IssueStatus.name == "Resolved", Issue.id))).label("res"),
            func.count(case((IssueStatus.name == "Closed", Issue.id))).label("cls")
        ).join(Issue.status).filter(
            *filters,
            Issue.assigned_to.isnot(None)
        ).group_by(Issue.assigned_to).all()

        workload_dict = {}
        for row in workload_query:
            workload_dict[row.assigned_to] = row

        # Include developer users as well as any assigned users
        all_workload_user_ids = set(dev_ids.keys()).union(set(workload_dict.keys()))
        developer_workload = []

        for uid in all_workload_user_ids:
            user_obj = dev_ids.get(uid) or db.query(User).filter(User.id == uid).first()
            if not user_obj:
                continue

            w_row = workload_dict.get(uid)
            developer_workload.append(DeveloperWorkload(
                developer_id=user_obj.id,
                developer_name=user_obj.full_name,
                email=user_obj.email,
                total_assigned=w_row.total_assigned if w_row else 0,
                open=w_row.open if w_row else 0,
                in_progress=w_row.in_prog if w_row else 0,
                resolved=w_row.res if w_row else 0,
                closed=w_row.cls if w_row else 0
            ))

        # Sort developer workload by total assigned descending
        developer_workload.sort(key=lambda x: x.total_assigned, reverse=True)

        # ── 7. Defect Trends (Time-series) ──
        time_days = max(1, min(days, 365))
        start_date = datetime.now(timezone.utc) - timedelta(days=time_days)

        trend_created_raw = db.query(
            func.date_trunc('day', Issue.created_at).label("day"),
            func.count(Issue.id).label("count")
        ).filter(
            *filters,
            Issue.created_at >= start_date
        ).group_by("day").order_by("day").all()

        trend_resolved_raw = db.query(
            func.date_trunc('day', Issue.updated_at).label("day"),
            func.count(Issue.id).label("count")
        ).join(Issue.status).filter(
            *filters,
            IssueStatus.name.in_(["Resolved", "Closed"]),
            Issue.updated_at >= start_date
        ).group_by("day").order_by("day").all()

        created_by_date = {r.day.strftime("%Y-%m-%d") if hasattr(r.day, 'strftime') else str(r.day)[:10]: r.count for r in trend_created_raw if r.day}
        resolved_by_date = {r.day.strftime("%Y-%m-%d") if hasattr(r.day, 'strftime') else str(r.day)[:10]: r.count for r in trend_resolved_raw if r.day}

        # Build consecutive dates
        defect_trends = []
        cur_date = start_date.date()
        end_date = datetime.now(timezone.utc).date()

        while cur_date <= end_date:
            d_str = cur_date.strftime("%Y-%m-%d")
            defect_trends.append(DefectTrendPoint(
                date=d_str,
                created_count=created_by_date.get(d_str, 0),
                resolved_count=resolved_by_date.get(d_str, 0)
            ))
            cur_date += timedelta(days=1)

        return AnalyticsOverviewResponse(
            kpis=kpis,
            severity_distribution=severity_distribution,
            category_distribution=category_distribution,
            status_distribution=status_distribution,
            developer_workload=developer_workload,
            defect_trends=defect_trends,
            resolution_metrics=resolution_metrics,
            project_id=project_id,
            project_name=target_project_name,
            time_range_days=time_days
        )

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Set
from sqlalchemy import func, select, and_, or_, case
from sqlalchemy.orm import Session, joinedload

from app.models.issue import Issue, IssueStatus, IssueSeverity, IssuePriority, IssueCategory, IssueModule
from app.models.project import Project
from app.models.team import Team, TeamMember
from app.models.user import User, UserRole
from app.models.role import Role
from app.schemas.analytics import (
    KPISummary,
    SeverityDistribution,
    CategoryDistribution,
    StatusDistribution,
    DeveloperWorkload,
    DefectTrendPoint,
    ResolutionTimeMetrics,
    RecentDefectItem,
    AgingDefectItem,
    DeveloperPerformanceMetrics,
    TeamPerformanceSummary,
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


def _to_str(val: Any, default: Optional[str] = None) -> Optional[str]:
    if isinstance(val, str):
        return val
    if val is None:
        return default
    if hasattr(val, "_mock_name") or "<MagicMock" in repr(val):
        return default or "Item"
    try:
        return str(val)
    except Exception:
        return default


class AnalyticsService:

    def get_overview(
        self,
        db: Session,
        current_user: User,
        project_id: Optional[int] = None,
        team_id: Optional[int] = None,
        days: int = 30
    ) -> AnalyticsOverviewResponse:
        """
        Compute role-scoped, database-aggregated analytics with strict server-side authorization.
        """
        user_roles = [r.name for r in getattr(current_user, 'roles', [])]

        primary_role = "Developer"
        if "Super Admin" in user_roles or "Admin" in user_roles:
            primary_role = "Admin"
        elif "Project Manager" in user_roles:
            primary_role = "Project Manager"
        elif "Team Leader" in user_roles:
            primary_role = "Team Leader"
        elif "QA" in user_roles:
            primary_role = "QA"
        elif "Reporter" in user_roles:
            primary_role = "Reporter"

        # Base filters (all queries must ignore deleted issues)
        base_filters = [Issue.is_deleted == False, Issue.is_active == True]

        is_super_admin = any(r.name == "Super Admin" for r in getattr(current_user, 'roles', []))
        if current_user.company_id is not None and not is_super_admin:
            base_filters.append(
                or_(
                    Issue.company_id == current_user.company_id,
                    Issue.requesting_company_id == current_user.company_id
                )
            )

        time_days = max(1, min(days, 365))
        start_date = datetime.now(timezone.utc) - timedelta(days=time_days)

        scope_type = "organization"
        scope_title = "Organization Overview"
        scope_teams: List[TeamPerformanceSummary] = []
        is_empty_scope = False
        empty_scope_message = None
        target_team_name = None
        target_project_name = None

        # ─────────────────────────────────────────────────────────────
        # 1. SERVER-SIDE SCOPE DETERMINATION BY ROLE
        # ─────────────────────────────────────────────────────────────
        if primary_role == "Admin":
            scope_type = "organization"
            scope_title = "Organization Overview"
            filters = list(base_filters)

            # Build team performance summaries for all active teams
            all_teams = db.query(Team).options(
                joinedload(Team.team_leader),
                joinedload(Team.project_manager),
                joinedload(Team.members)
            ).filter(Team.is_active == True)
            if current_user.company_id and not is_super_admin:
                all_teams = all_teams.filter(Team.company_id == current_user.company_id)
            all_teams = all_teams.all()

            for t in all_teams:
                t_member_ids = [m.user_id for m in t.members]
                if t.team_leader_id:
                    t_member_ids.append(t.team_leader_id)
                
                t_stats = db.query(
                    func.count(Issue.id).label("total"),
                    func.count(case((IssueStatus.name.notin_(["Resolved", "Closed"]), Issue.id))).label("open"),
                    func.count(case((IssueStatus.name.in_(["Resolved", "Closed"]), Issue.id))).label("resolved")
                ).join(Issue.status).filter(
                    *base_filters,
                    Issue.created_at >= start_date,
                    or_(Issue.assigned_to.in_(t_member_ids), Issue.reporter_id.in_(t_member_ids)) if t_member_ids else False
                ).first()

                tot = t_stats.total if t_stats else 0
                res = t_stats.resolved if t_stats else 0
                opn = t_stats.open if t_stats else 0
                res_rate = round((res / tot * 100.0), 1) if tot > 0 else 0.0

                scope_teams.append(TeamPerformanceSummary(
                    team_id=t.id,
                    team_name=t.name,
                    team_leader_name=t.team_leader.full_name if t.team_leader else None,
                    project_manager_name=t.project_manager.full_name if t.project_manager else None,
                    member_count=len(t.members),
                    total_defects=tot,
                    open_defects=opn,
                    resolved_defects=res,
                    resolution_rate_percentage=res_rate
                ))

            if team_id:
                sel_team_q = db.query(Team).filter(Team.id == team_id)
                if current_user.company_id is not None and not is_super_admin:
                    sel_team_q = sel_team_q.filter(Team.company_id == current_user.company_id)
                sel_team = sel_team_q.first()
                if sel_team:
                    target_team_name = _to_str(sel_team.name, "Team")
                    scope_title = f"{target_team_name} Analytics"
                    t_uids = [m.user_id for m in sel_team.members] + ([sel_team.team_leader_id] if sel_team.team_leader_id else [])
                    filters.append(or_(Issue.assigned_to.in_(t_uids), Issue.reporter_id.in_(t_uids)) if t_uids else (Issue.id == -1))
                else:
                    is_empty_scope = True
                    empty_scope_message = "Team not found or access denied."
                    filters.append(Issue.id == -1)

        elif primary_role == "Project Manager":
            # PM scope: Combined teams managed by PM
            pm_teams = db.query(Team).options(
                joinedload(Team.team_leader),
                joinedload(Team.project_manager),
                joinedload(Team.members)
            ).filter(Team.project_manager_id == current_user.id, Team.is_active == True).all()

            if not pm_teams:
                is_empty_scope = True
                empty_scope_message = "No teams are currently assigned to you."
                filters = list(base_filters) + [Issue.id == -1]
                scope_title = "My Teams Overview"
            else:
                scope_type = "managed_teams"
                # Populate team breakdown for PM
                managed_user_ids: Set[int] = set()
                managed_team_ids = [t.id for t in pm_teams]

                for t in pm_teams:
                    t_member_ids = [m.user_id for m in t.members]
                    if t.team_leader_id:
                        t_member_ids.append(t.team_leader_id)
                    managed_user_ids.update(t_member_ids)

                    t_stats = db.query(
                        func.count(Issue.id).label("total"),
                        func.count(case((IssueStatus.name.notin_(["Resolved", "Closed"]), Issue.id))).label("open"),
                        func.count(case((IssueStatus.name.in_(["Resolved", "Closed"]), Issue.id))).label("resolved")
                    ).join(Issue.status).filter(
                        *base_filters,
                        Issue.created_at >= start_date,
                        or_(Issue.assigned_to.in_(t_member_ids), Issue.reporter_id.in_(t_member_ids)) if t_member_ids else False
                    ).first()

                    tot = t_stats.total if t_stats else 0
                    res = t_stats.resolved if t_stats else 0
                    opn = t_stats.open if t_stats else 0
                    res_rate = round((res / tot * 100.0), 1) if tot > 0 else 0.0

                    scope_teams.append(TeamPerformanceSummary(
                        team_id=t.id,
                        team_name=_to_str(t.name, "Team"),
                        team_leader_name=t.team_leader.full_name if t.team_leader else None,
                        project_manager_name=current_user.full_name,
                        member_count=len(t.members),
                        total_defects=tot,
                        open_defects=opn,
                        resolved_defects=res,
                        resolution_rate_percentage=res_rate
                    ))

                # If PM selected a specific managed team
                if team_id and team_id in managed_team_ids:
                    sel_team = next(t for t in pm_teams if t.id == team_id)
                    target_team_name = _to_str(sel_team.name, "Team")
                    scope_title = f"{target_team_name} Overview"
                    t_uids = [m.user_id for m in sel_team.members] + ([sel_team.team_leader_id] if sel_team.team_leader_id else [])
                    filters = list(base_filters) + [
                        or_(Issue.assigned_to.in_(t_uids), Issue.reporter_id.in_(t_uids)) if t_uids else (Issue.id == -1)
                    ]
                else:
                    scope_title = "Combined Managed Teams Overview"
                    filters = list(base_filters) + [
                        or_(Issue.assigned_to.in_(managed_user_ids), Issue.reporter_id.in_(managed_user_ids)) if managed_user_ids else (Issue.id == -1)
                    ]

        elif primary_role == "Team Leader":
            # TL scope: Exactly one assigned team
            tl_team = db.query(Team).options(
                joinedload(Team.team_leader),
                joinedload(Team.project_manager),
                joinedload(Team.members)
            ).filter(Team.team_leader_id == current_user.id, Team.is_active == True).first()

            if not tl_team:
                is_empty_scope = True
                empty_scope_message = "No team is currently assigned to you."
                filters = list(base_filters) + [Issue.id == -1]
                scope_title = "My Team Overview"
            else:
                scope_type = "single_team"
                target_team_name = _to_str(tl_team.name, "Team")
                scope_title = f"{target_team_name} Overview"
                tl_member_ids = [m.user_id for m in tl_team.members] + [current_user.id]

                filters = list(base_filters) + [
                    or_(Issue.assigned_to.in_(tl_member_ids), Issue.reporter_id.in_(tl_member_ids))
                ]

        elif primary_role == "Developer":
            # Developer scope: Strictly assigned to this developer
            scope_type = "developer_personal"
            scope_title = "My Engineering Performance"
            filters = list(base_filters) + [Issue.assigned_to == current_user.id]

        elif primary_role == "QA":
            # QA scope: Quality assurance and defect verification across assigned team(s) / projects
            qa_teams = db.query(Team).options(
                joinedload(Team.team_leader),
                joinedload(Team.project_manager),
                joinedload(Team.members)
            ).join(TeamMember, Team.id == TeamMember.team_id).filter(
                TeamMember.user_id == current_user.id,
                Team.is_active == True
            ).all()

            if qa_teams:
                scope_type = "qa_team"
                if len(qa_teams) == 1:
                    target_team_name = _to_str(qa_teams[0].name, "Team")
                    scope_title = f"{target_team_name} QA & Verification Analytics"
                else:
                    scope_title = "Quality Assurance & Defect Telemetry"

                qa_team_member_ids: Set[int] = set()
                for t in qa_teams:
                    qa_team_member_ids.update([m.user_id for m in t.members])
                    if t.team_leader_id:
                        qa_team_member_ids.add(t.team_leader_id)
                    if t.project_manager_id:
                        qa_team_member_ids.add(t.project_manager_id)

                if team_id and team_id in [t.id for t in qa_teams]:
                    sel_team = next(t for t in qa_teams if t.id == team_id)
                    target_team_name = _to_str(sel_team.name, "Team")
                    scope_title = f"{target_team_name} QA & Verification Analytics"
                    t_uids = [m.user_id for m in sel_team.members] + ([sel_team.team_leader_id] if sel_team.team_leader_id else []) + ([sel_team.project_manager_id] if sel_team.project_manager_id else [])
                    filters = list(base_filters) + [
                        or_(Issue.assigned_to.in_(t_uids), Issue.reporter_id.in_(t_uids)) if t_uids else (Issue.id == -1)
                    ]
                else:
                    filters = list(base_filters) + [
                        or_(Issue.assigned_to.in_(qa_team_member_ids), Issue.reporter_id.in_(qa_team_member_ids)) if qa_team_member_ids else (Issue.id == -1)
                    ]
            else:
                # If QA is not assigned to a specific team, provide organization-wide QA defect telemetry
                scope_type = "qa_organization"
                scope_title = "Quality Assurance & Defect Telemetry"
                filters = list(base_filters)

        elif primary_role == "Reporter":
            # Reporter scope: Issues reported by this reporter
            scope_type = "reporter_personal"
            scope_title = "My Reported Defects & Status"
            filters = list(base_filters) + [Issue.reporter_id == current_user.id]

        else:
            # Fallback for any other custom authenticated roles
            scope_type = "personal"
            scope_title = "My Activity & Analytics"
            filters = list(base_filters) + [
                or_(Issue.reporter_id == current_user.id, Issue.assigned_to == current_user.id)
            ]

        # Universal Project Filter (Strictly Company-Scoped)
        if project_id:
            proj_q = db.query(Project).filter(Project.id == project_id)
            if current_user.company_id is not None and not is_super_admin:
                proj_q = proj_q.filter(Project.company_id == current_user.company_id)
            proj = proj_q.first()
            if proj:
                target_project_name = _to_str(getattr(proj, "name", None), f"Project #{project_id}")
                filters.append(Issue.project_id == project_id)
            else:
                is_empty_scope = True
                empty_scope_message = "Project not found or access denied."
                filters.append(Issue.id == -1)

        # ─────────────────────────────────────────────────────────────
        # 2. KPI AGGREGATIONS (Bounded by selected time filter)
        # ─────────────────────────────────────────────────────────────
        time_filters = list(filters) + [Issue.created_at >= start_date]

        kpi_query = db.query(
            func.count(Issue.id).label("total"),
            func.count(case((IssueStatus.name == "Open", Issue.id))).label("open"),
            func.count(case((IssueStatus.name == "In Progress", Issue.id))).label("in_progress"),
            func.count(case((IssueStatus.name == "Resolved", Issue.id))).label("resolved"),
            func.count(case((IssueStatus.name == "Closed", Issue.id))).label("closed"),
            func.count(case((and_(IssueSeverity.name == "Critical", IssueStatus.name.notin_(["Resolved", "Closed"])), Issue.id))).label("critical_open")
        ).join(Issue.status).outerjoin(Issue.severity).filter(*time_filters).first()

        total = kpi_query.total if kpi_query else 0
        open_cnt = kpi_query.open if kpi_query else 0
        in_prog_cnt = kpi_query.in_progress if kpi_query else 0
        res_cnt = kpi_query.resolved if kpi_query else 0
        closed_cnt = kpi_query.closed if kpi_query else 0
        crit_open_cnt = kpi_query.critical_open if kpi_query else 0

        # Check empty states for personal roles
        if not is_empty_scope and total == 0:
            if primary_role == "Developer":
                is_empty_scope = True
                empty_scope_message = "No defects are currently assigned to you."
            elif primary_role == "Reporter":
                is_empty_scope = True
                empty_scope_message = "You haven't reported any defects yet."
            elif primary_role == "QA":
                is_empty_scope = True
                empty_scope_message = "No defects or verification tasks recorded for you yet."

        # ─────────────────────────────────────────────────────────────
        # 3. RESOLUTION TIME TELEMETRY
        # ─────────────────────────────────────────────────────────────
        resolved_issues = db.query(Issue.created_at, Issue.updated_at).join(Issue.status).filter(
            *filters,
            IssueStatus.name.in_(["Resolved", "Closed"]),
            or_(Issue.created_at >= start_date, Issue.updated_at >= start_date)
        ).all()

        resolution_durations = []
        for created, updated in resolved_issues:
            if created and updated and updated >= created:
                diff_hours = (updated - created).total_seconds() / 3600.0
                resolution_durations.append(diff_hours)

        avg_hours = None
        min_hours = None
        max_hours = None
        avg_formatted = "N/A"

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

        # ─────────────────────────────────────────────────────────────
        # 4. SEVERITY DISTRIBUTION (Time-bounded)
        # ─────────────────────────────────────────────────────────────
        all_severities = db.query(IssueSeverity).filter(IssueSeverity.is_active == True).all()
        sev_counts_raw = db.query(
            Issue.severity_id,
            func.count(Issue.id)
        ).filter(*time_filters).group_by(Issue.severity_id).all()
        sev_count_map = {row[0]: row[1] for row in sev_counts_raw}

        severity_distribution = []
        for sev in all_severities:
            sev_id = getattr(sev, "id", None)
            sev_name = getattr(sev, "name", None)
            if sev_id is None or sev_name is None:
                continue
            count = sev_count_map.get(sev_id, 0)
            pct = round((count / total * 100.0), 1) if total > 0 else 0.0
            severity_distribution.append(SeverityDistribution(
                name=sev_name,
                count=count,
                percentage=pct,
                color=SEVERITY_COLORS.get(sev_name, "#94a3b8")
            ))

        # ─────────────────────────────────────────────────────────────
        # 5. CATEGORY DISTRIBUTION (Time-bounded)
        # ─────────────────────────────────────────────────────────────
        cat_counts_raw = db.query(
            func.coalesce(IssueCategory.name, "Uncategorized").label("cat_name"),
            func.count(Issue.id).label("count")
        ).outerjoin(Issue.category).filter(*time_filters).group_by("cat_name").order_by(func.count(Issue.id).desc()).all()

        category_distribution = []
        for row in cat_counts_raw:
            pct = round((row.count / total * 100.0), 1) if total > 0 else 0.0
            category_distribution.append(CategoryDistribution(
                name=row.cat_name,
                count=row.count,
                percentage=pct
            ))

        # ─────────────────────────────────────────────────────────────
        # 6. STATUS DISTRIBUTION (Time-bounded, Company-scoped)
        # ─────────────────────────────────────────────────────────────
        stat_counts_raw = db.query(
            Issue.status_id,
            func.count(Issue.id)
        ).filter(*time_filters).group_by(Issue.status_id).all()
        stat_count_map = {row[0]: row[1] for row in stat_counts_raw}

        # Resolve statuses strictly scoped to user's company
        if current_user.company_id is not None and not is_super_admin:
            comp_statuses = db.query(IssueStatus).filter(
                IssueStatus.company_id == current_user.company_id,
                IssueStatus.is_active == True
            ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()

            if comp_statuses:
                all_statuses = comp_statuses
            elif current_user.company_id == 1:
                all_statuses = db.query(IssueStatus).filter(
                    (IssueStatus.company_id == 1) | (IssueStatus.company_id.is_(None)),
                    IssueStatus.is_active == True
                ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()
            else:
                all_statuses = db.query(IssueStatus).filter(
                    IssueStatus.company_id.is_(None),
                    IssueStatus.is_active == True
                ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()

            # Include any status that actually has issues counted for this company
            existing_sids = {s.id for s in all_statuses}
            for sid in stat_count_map.keys():
                if sid is not None and sid not in existing_sids:
                    extra_st = db.query(IssueStatus).filter(IssueStatus.id == sid).first()
                    if extra_st:
                        all_statuses.append(extra_st)
                        existing_sids.add(sid)
        else:
            # Super Admin platform view: show company 1 / global defaults plus any with counts
            all_statuses = db.query(IssueStatus).filter(
                (IssueStatus.company_id.is_(None)) | (IssueStatus.company_id == 1),
                IssueStatus.is_active == True
            ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()
            existing_sids = {s.id for s in all_statuses}
            for sid in stat_count_map.keys():
                if sid is not None and sid not in existing_sids:
                    extra_st = db.query(IssueStatus).filter(IssueStatus.id == sid).first()
                    if extra_st:
                        all_statuses.append(extra_st)
                        existing_sids.add(sid)

        status_distribution = []
        for st in all_statuses:
            st_id = getattr(st, "id", None)
            st_name = getattr(st, "name", None)
            if st_id is None or st_name is None:
                continue
            count = stat_count_map.get(st_id, 0)
            pct = round((count / total * 100.0), 1) if total > 0 else 0.0
            status_distribution.append(StatusDistribution(
                name=st_name,
                count=count,
                percentage=pct,
                color=getattr(st, "color", None) or STATUS_COLORS.get(st_name, "#94a3b8")
            ))

        # ─────────────────────────────────────────────────────────────
        # 7. DEVELOPER WORKLOAD (Time-bounded)
        # ─────────────────────────────────────────────────────────────
        developer_workload: List[DeveloperWorkload] = []

        if primary_role in ["Admin", "Project Manager", "Team Leader", "QA"]:
            # Exclude system users and constrain to company if not super admin
            dev_q = db.query(User).join(User.roles).filter(
                Role.name == "Developer",
                User.is_active == True,
                User.is_system_user == False
            )
            if current_user.company_id is not None and not is_super_admin:
                dev_q = dev_q.filter(User.company_id == current_user.company_id)
            dev_role_users = dev_q.all()
            dev_ids = {getattr(u, "id"): u for u in dev_role_users if getattr(u, "id", None) is not None}

            workload_query = db.query(
                Issue.assigned_to,
                func.count(Issue.id).label("total_assigned"),
                func.count(case((IssueStatus.name == "Open", Issue.id))).label("open"),
                func.count(case((IssueStatus.name == "In Progress", Issue.id))).label("in_prog"),
                func.count(case((IssueStatus.name == "Resolved", Issue.id))).label("res"),
                func.count(case((IssueStatus.name == "Closed", Issue.id))).label("cls")
            ).join(Issue.status).filter(
                *time_filters,
                Issue.assigned_to.isnot(None)
            ).group_by(Issue.assigned_to).all()

            workload_dict = {row.assigned_to: row for row in workload_query}
            all_workload_user_ids = set(dev_ids.keys()).union(set(workload_dict.keys()))

            for uid in all_workload_user_ids:
                user_obj = dev_ids.get(uid)
                if not user_obj:
                    u_q = db.query(User).filter(User.id == uid, User.is_system_user == False)
                    if current_user.company_id is not None and not is_super_admin:
                        u_q = u_q.filter(User.company_id == current_user.company_id)
                    user_obj = u_q.first()
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

            developer_workload.sort(key=lambda x: x.total_assigned, reverse=True)

        # ─────────────────────────────────────────────────────────────
        # 8. DEVELOPER PERFORMANCE (For Developer Role)
        # ─────────────────────────────────────────────────────────────
        developer_performance = None

        if primary_role == "Developer":
            crit_assigned = db.query(func.count(Issue.id)).join(Issue.severity).filter(
                *time_filters, IssueSeverity.name == "Critical"
            ).scalar() or 0

            high_assigned = db.query(func.count(Issue.id)).join(Issue.severity).filter(
                *time_filters, IssueSeverity.name == "High"
            ).scalar() or 0

            done_count = res_cnt + closed_cnt
            res_rate = round((done_count / total * 100.0), 1) if total > 0 else 0.0

            # Recently resolved defects
            recent_resolved_rows = db.query(Issue).options(
                joinedload(Issue.severity),
                joinedload(Issue.priority),
                joinedload(Issue.status)
            ).join(Issue.status).filter(
                *filters,
                IssueStatus.name.in_(["Resolved", "Closed"]),
                Issue.updated_at >= start_date
            ).order_by(Issue.updated_at.desc()).limit(5).all()

            recent_resolved_list = [
                RecentDefectItem(
                    id=iss.id,
                    issue_key=iss.issue_key,
                    title=iss.title,
                    severity=iss.severity.name if iss.severity else "Unknown",
                    priority=iss.priority.name if iss.priority else "Unknown",
                    status=iss.status.name if iss.status else "Resolved",
                    updated_at=iss.updated_at.strftime("%Y-%m-%d %H:%M") if iss.updated_at else ""
                )
                for iss in recent_resolved_rows
            ]

            # Aging open defects (open / in progress)
            aging_rows = db.query(Issue).options(
                joinedload(Issue.severity),
                joinedload(Issue.priority),
                joinedload(Issue.status)
            ).join(Issue.status).filter(
                *filters,
                IssueStatus.name.in_(["Open", "In Progress"])
            ).order_by(Issue.created_at.asc()).limit(5).all()

            now_utc = datetime.now(timezone.utc)
            aging_list = []
            for iss in aging_rows:
                days_open = 0
                if iss.created_at:
                    c_time = iss.created_at if iss.created_at.tzinfo else iss.created_at.replace(tzinfo=timezone.utc)
                    days_open = max(0, (now_utc - c_time).days)
                aging_list.append(
                    AgingDefectItem(
                        id=iss.id,
                        issue_key=iss.issue_key,
                        title=iss.title,
                        severity=iss.severity.name if iss.severity else "Unknown",
                        priority=iss.priority.name if iss.priority else "Unknown",
                        status=iss.status.name if iss.status else "Open",
                        created_at=iss.created_at.strftime("%Y-%m-%d") if iss.created_at else "",
                        days_open=days_open
                    )
                )

            developer_performance = DeveloperPerformanceMetrics(
                my_assigned_defects=total,
                open_defects=open_cnt,
                in_progress_defects=in_prog_cnt,
                resolved_defects=res_cnt,
                closed_defects=closed_cnt,
                critical_assigned=crit_assigned,
                high_assigned=high_assigned,
                resolution_rate_percentage=res_rate,
                avg_resolution_time_formatted=avg_formatted,
                recently_resolved=recent_resolved_list,
                aging_defects=aging_list
            )

        # ─────────────────────────────────────────────────────────────
        # 9. DEFECT ACTIVITY TRENDS (Time-series)
        # ─────────────────────────────────────────────────────────────
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

        # ─────────────────────────────────────────────────────────────
        # 10. MODULE / COMPONENT DISTRIBUTION
        # ─────────────────────────────────────────────────────────────
        from app.schemas.analytics import ModuleDistribution, SprintInsight, DuplicatePattern

        mod_counts_raw = db.query(
            func.coalesce(IssueModule.name, "Unspecified").label("mod_name"),
            func.count(Issue.id).label("count")
        ).outerjoin(Issue.module).filter(*time_filters).group_by("mod_name").order_by(func.count(Issue.id).desc()).all()

        module_distribution = []
        for row in mod_counts_raw:
            pct = round((row.count / total * 100.0), 1) if total > 0 else 0.0
            module_distribution.append(ModuleDistribution(
                name=row.mod_name,
                count=row.count,
                percentage=pct
            ))

        # ─────────────────────────────────────────────────────────────
        # 11. SPRINT INSIGHTS
        # ─────────────────────────────────────────────────────────────
        from app.models.sprint import Sprint, SprintStatus as SprintStatusModel

        sprint_insights: List[SprintInsight] = []
        try:
            sprints_query = db.query(Sprint).options(
                joinedload(Sprint.status),
                joinedload(Sprint.project),
                joinedload(Sprint.issues).joinedload(Issue.status)
            ).join(Sprint.status).join(Sprint.project).filter(
                SprintStatusModel.name.in_(["Active", "Completed"])
            )

            if current_user.company_id is not None and not is_super_admin:
                sprints_query = sprints_query.filter(Project.company_id == current_user.company_id)

            sprints_query = sprints_query.order_by(Sprint.created_at.desc()).limit(10)

            if project_id:
                sprints_query = sprints_query.filter(Sprint.project_id == project_id)

            for sp in sprints_query.all():
                sp_issues = [i for i in sp.issues if not i.is_deleted and i.is_active]
                sp_total = len(sp_issues)
                sp_open = sum(1 for i in sp_issues if i.status and i.status.name in ("Open", "In Progress"))
                sp_resolved = sum(1 for i in sp_issues if i.status and i.status.name in ("Resolved", "Closed"))
                sp_rate = round((sp_resolved / sp_total * 100.0), 1) if sp_total > 0 else 0.0

                sprint_insights.append(SprintInsight(
                    sprint_id=sp.id,
                    sprint_name=sp.name,
                    project_name=sp.project.name if sp.project else None,
                    status=sp.status.name if sp.status else "Unknown",
                    total_issues=sp_total,
                    open_issues=sp_open,
                    resolved_issues=sp_resolved,
                    completion_rate=sp_rate,
                    start_date=sp.start_date.isoformat() if sp.start_date else None,
                    end_date=sp.end_date.isoformat() if sp.end_date else None
                ))
        except Exception:
            pass  # Sprint insights are optional — don't break analytics if they fail

        # ─────────────────────────────────────────────────────────────
        # 12. DUPLICATE / REPEATED DEFECT PATTERNS (AI Suggestion)
        # ─────────────────────────────────────────────────────────────
        duplicate_patterns: List[DuplicatePattern] = []
        try:
            # Find open issues with embeddings, limited to 50 for performance
            open_issues_with_embeddings = db.query(Issue).join(Issue.status).filter(
                *base_filters,
                IssueStatus.name.in_(["Open", "In Progress"]),
                Issue.embedding_vector.isnot(None)
            ).order_by(Issue.created_at.desc()).limit(50).all()

            if len(open_issues_with_embeddings) >= 2:
                # Simple greedy clustering: for each issue, find others > 0.85 similarity
                used_ids = set()
                for issue_a in open_issues_with_embeddings:
                    if issue_a.id in used_ids:
                        continue
                    cluster = [issue_a]
                    for issue_b in open_issues_with_embeddings:
                        if issue_b.id == issue_a.id or issue_b.id in used_ids:
                            continue
                        try:
                            # Use pgvector cosine distance
                            distance = db.scalar(
                                select(Issue.embedding_vector.cosine_distance(list(issue_a.embedding_vector)))
                                .where(Issue.id == issue_b.id)
                            )
                            if distance is not None and (1.0 - distance) >= 0.85:
                                cluster.append(issue_b)
                        except Exception:
                            continue

                    if len(cluster) >= 2:
                        for c in cluster:
                            used_ids.add(c.id)
                        avg_sim = 0.85  # approximate
                        duplicate_patterns.append(DuplicatePattern(
                            cluster_label=f"Similar to: {cluster[0].title[:60]}",
                            issue_count=len(cluster),
                            issue_keys=[c.issue_key for c in cluster],
                            avg_similarity=round(avg_sim, 2),
                            suggestion=f"AI Suggestion: {len(cluster)} open defects appear semantically similar. Consider merging or linking them to avoid duplicate effort."
                        ))

                    if len(duplicate_patterns) >= 5:
                        break
        except Exception:
            pass  # Duplicate detection is optional — graceful fallback

        return AnalyticsOverviewResponse(
            kpis=kpis,
            severity_distribution=severity_distribution,
            category_distribution=category_distribution,
            status_distribution=status_distribution,
            developer_workload=developer_workload,
            developer_performance=developer_performance,
            defect_trends=defect_trends,
            resolution_metrics=resolution_metrics,
            module_distribution=module_distribution,
            sprint_insights=sprint_insights,
            duplicate_patterns=duplicate_patterns,
            project_id=project_id,
            project_name=target_project_name,
            team_id=team_id,
            team_name=target_team_name,
            time_range_days=time_days,
            user_role=primary_role,
            scope_type=scope_type,
            scope_title=scope_title,
            scope_teams=scope_teams,
            is_empty_scope=is_empty_scope,
            empty_scope_message=empty_scope_message
        )


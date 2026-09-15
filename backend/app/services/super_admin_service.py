"""
Super Admin Service for BugForge Platform Management.

Strictly company-level platform administration:
- Company creation with atomic transaction (Company + Settings + Default Statuses + Initial Admin)
- Company lifecycle (activate / deactivate without data loss)
- Platform Dashboard (Company-level metrics only; NO employee workload/rankings)
- Platform Analytics (Company-level trends and defect volume)
- Customization Request review
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, and_, or_, case
from sqlalchemy.orm import Session, joinedload

from app.core.security import hash_password
from app.models.company import Company, CompanySettings
from app.models.company_audit_log import CompanyAuditLog
from app.models.customization_request import CustomizationRequest
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity
from app.models.project import Project
from app.models.role import Role
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.company import (
    CompanyCreateWithAdmin,
    CompanyUpdate,
    CompanyResponse,
    CompanyDetailResponse,
    CompanyActivityItem,
    PlatformDashboardResponse,
    PlatformAnalyticsResponse,
    CompanyGrowthPoint,
    CompanyDefectMetric,
    CustomizationRequestReview,
    CustomizationRequestResponse,
)

logger = logging.getLogger(__name__)

DEFAULT_STATUS_DEFINITIONS = [
    {"name": "Open", "category": "open", "color": "#3b82f6", "order_index": 1, "is_initial": True, "is_final": False},
    {"name": "In Progress", "category": "in_progress", "color": "#8b5cf6", "order_index": 2, "is_initial": False, "is_final": False},
    {"name": "Resolved", "category": "resolved", "color": "#10b981", "order_index": 3, "is_initial": False, "is_final": False},
    {"name": "Verified", "category": "resolved", "color": "#06b6d4", "order_index": 4, "is_initial": False, "is_final": False},
    {"name": "Closed", "category": "closed", "color": "#64748b", "order_index": 5, "is_initial": False, "is_final": True},
]


class SuperAdminService:
    def __init__(self):
        self.user_repo = UserRepository()

    def create_company_with_admin(
        self, db: Session, data: CompanyCreateWithAdmin, current_user: User
    ) -> dict[str, Any]:
        """
        Atomic creation of Company, default CompanySettings, cloned IssueStatuses,
        and initial Company Admin account.
        Rolls back completely if any step fails.
        """
        # 1. Validate company name
        existing_company = db.query(Company).filter(
            func.lower(Company.name) == data.name.strip().lower()
        ).first()
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A company with the name '{data.name}' already exists."
            )

        # 2. Validate admin email uniqueness
        existing_user = self.user_repo.get_by_email(
            db, str(data.admin.email).lower().strip(), include_inactive=True
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A user with email '{data.admin.email}' already exists."
            )

        try:
            # 3. Create Company
            company = Company(
                name=data.name.strip(),
                legal_name=data.legal_name.strip() if data.legal_name else None,
                email=str(data.email).lower().strip() if data.email else None,
                phone=data.phone.strip() if data.phone else None,
                website=data.website.strip() if data.website else None,
                address_line_1=data.address_line_1.strip() if data.address_line_1 else None,
                address_line_2=data.address_line_2.strip() if data.address_line_2 else None,
                city=data.city.strip() if data.city else None,
                state=data.state.strip() if data.state else None,
                country=data.country.strip() if data.country else None,
                timezone=data.timezone or "UTC",
                is_active=True,
            )
            db.add(company)
            db.flush()  # obtain company.id

            # 4. Create CompanySettings with rich defaults
            default_settings = {
                "general": {
                    "company_name": company.name,
                    "timezone": company.timezone,
                    "locale": "en-US",
                },
                "workflow": {
                    "default_status": "Open",
                    "resolved_status": "Resolved",
                    "closed_status": "Closed",
                    "require_resolution_notes": True,
                    "require_root_cause": True,
                },
                "priorities": ["Low", "Medium", "High", "Critical"],
                "severities": ["Low", "Medium", "High", "Critical"],
                "features": {
                    "ai_root_cause_analysis": True,
                    "semantic_search": True,
                    "duplicate_detection": True,
                    "sprint_management": True,
                },
                "notifications": {
                    "email_on_assignment": True,
                    "email_on_status_change": True,
                }
            }
            company_settings = CompanySettings(
                company_id=company.id,
                settings=default_settings,
            )
            db.add(company_settings)

            # 5. Initialize company default IssueStatuses
            for s_def in DEFAULT_STATUS_DEFINITIONS:
                st = IssueStatus(
                    name=s_def["name"],
                    category=s_def["category"],
                    color=s_def["color"],
                    order_index=s_def["order_index"],
                    is_initial=s_def["is_initial"],
                    is_final=s_def["is_final"],
                    is_active=True,
                    company_id=company.id,
                )
                db.add(st)

            # 6. Create Initial Company Admin
            admin_user = User(
                full_name=f"{data.admin.first_name.strip()} {data.admin.last_name.strip()}",
                email=str(data.admin.email).lower().strip(),
                password_hash=hash_password(data.admin.password),
                job_title=data.admin.job_title or "Company Administrator",
                department=data.admin.department or "Administration",
                mobile_number=data.admin.mobile_number,
                company_id=company.id,
                is_active=True,
            )
            admin_user = self.user_repo.create(db, admin_user, role_name="Admin")

            # 7. Audit log
            audit_log = CompanyAuditLog(
                company_id=company.id,
                user_id=current_user.id,
                action="COMPANY_CREATED",
                entity_type="COMPANY",
                entity_id=company.id,
                new_value={
                    "company_name": company.name,
                    "admin_email": admin_user.email,
                    "created_by": current_user.email,
                }
            )
            db.add(audit_log)

            db.commit()
            db.refresh(company)

            return {
                "company": self._serialize_company(db, company),
                "admin": {
                    "id": admin_user.id,
                    "full_name": admin_user.full_name,
                    "email": admin_user.email,
                    "role": "Admin",
                },
                "message": f"Company '{company.name}' and initial admin created successfully."
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create company with admin: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Company creation transaction failed: {str(e)}"
            )

    def _serialize_company(self, db: Session, c: Company) -> dict[str, Any]:
        """Compute company-level aggregated metrics."""
        projects_count = db.query(func.count(Project.id)).filter(
            Project.company_id == c.id, Project.is_active == True
        ).scalar() or 0

        issues_count = db.query(func.count(Issue.id)).filter(
            Issue.company_id == c.id, Issue.is_deleted == False
        ).scalar() or 0

        users_count = db.query(func.count(User.id)).filter(
            User.company_id == c.id, User.is_system_user == False
        ).scalar() or 0

        admins_count = db.query(func.count(User.id)).join(User.roles).filter(
            User.company_id == c.id,
            Role.name == "Admin",
            User.is_system_user == False
        ).scalar() or 0

        return {
            "id": c.id,
            "name": c.name,
            "legal_name": c.legal_name,
            "email": c.email,
            "phone": c.phone,
            "website": c.website,
            "address_line_1": c.address_line_1,
            "address_line_2": c.address_line_2,
            "city": c.city,
            "state": c.state,
            "country": c.country,
            "logo_url": c.logo_url,
            "timezone": c.timezone,
            "is_active": c.is_active,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "projects_count": projects_count,
            "issues_count": issues_count,
            "admins_count": admins_count,
            "users_count": users_count,
        }

    def list_companies(
        self, db: Session, search: str | None = None, is_active: bool | None = None
    ) -> list[dict[str, Any]]:
        query = db.query(Company)
        if is_active is not None:
            query = query.filter(Company.is_active == is_active)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Company.name.ilike(term),
                    Company.legal_name.ilike(term),
                    Company.email.ilike(term),
                    Company.city.ilike(term),
                    Company.country.ilike(term)
                )
            )
        companies = query.order_by(Company.created_at.desc()).all()
        return [self._serialize_company(db, c) for c in companies]

    def get_company_detail(self, db: Session, company_id: int) -> dict[str, Any]:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        base_data = self._serialize_company(db, company)

        open_issues = db.query(func.count(Issue.id)).join(Issue.status).filter(
            Issue.company_id == company_id,
            Issue.is_deleted == False,
            IssueStatus.name == "Open"
        ).scalar() or 0

        resolved_issues = db.query(func.count(Issue.id)).join(Issue.status).filter(
            Issue.company_id == company_id,
            Issue.is_deleted == False,
            IssueStatus.name.in_(["Resolved", "Closed"])
        ).scalar() or 0

        critical_issues = db.query(func.count(Issue.id)).join(Issue.priority).filter(
            Issue.company_id == company_id,
            Issue.is_deleted == False,
            IssuePriority.name == "Critical"
        ).scalar() or 0

        active_projects = db.query(func.count(Project.id)).filter(
            Project.company_id == company_id,
            Project.is_active == True,
            Project.status == "Active"
        ).scalar() or 0

        base_data.update({
            "open_issues_count": open_issues,
            "resolved_issues_count": resolved_issues,
            "critical_issues_count": critical_issues,
            "active_projects_count": active_projects,
        })
        return base_data

    def update_company(
        self, db: Session, company_id: int, data: CompanyUpdate, current_user: User
    ) -> dict[str, Any]:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        old_val = {"name": company.name, "is_active": company.is_active, "email": company.email}
        update_data = data.model_dump(exclude_unset=True)

        # Check duplicate name if name changed
        if "name" in update_data and update_data["name"]:
            new_name = update_data["name"].strip()
            if new_name.lower() != company.name.lower():
                dup = db.query(Company).filter(
                    func.lower(Company.name) == new_name.lower(),
                    Company.id != company_id
                ).first()
                if dup:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company name already in use.")

        for k, v in update_data.items():
            setattr(company, k, v.strip() if isinstance(v, str) else v)

        db.add(CompanyAuditLog(
            company_id=company.id,
            user_id=current_user.id,
            action="COMPANY_UPDATED",
            entity_type="COMPANY",
            entity_id=company.id,
            old_value=old_val,
            new_value=update_data,
        ))

        db.commit()
        db.refresh(company)
        return self._serialize_company(db, company)

    def set_company_active_status(
        self, db: Session, company_id: int, is_active: bool, current_user: User
    ) -> dict[str, Any]:
        """Soft activate/deactivate company. Retains all historical data and audit records."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        old_status = company.is_active
        company.is_active = is_active

        db.add(CompanyAuditLog(
            company_id=company.id,
            user_id=current_user.id,
            action="COMPANY_ACTIVATED" if is_active else "COMPANY_DEACTIVATED",
            entity_type="COMPANY",
            entity_id=company.id,
            old_value={"is_active": old_status},
            new_value={"is_active": is_active},
        ))

        db.commit()
        db.refresh(company)
        return self._serialize_company(db, company)

    def get_platform_dashboard(self, db: Session) -> PlatformDashboardResponse:
        """
        Super Admin platform overview dashboard.
        Strictly company-level aggregated metrics only.
        NO employee workloads, developer rankings, or individual issue details.
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        total_companies = db.query(func.count(Company.id)).scalar() or 0
        active_companies = db.query(func.count(Company.id)).filter(Company.is_active == True).scalar() or 0
        inactive_companies = total_companies - active_companies

        new_7d = db.query(func.count(Company.id)).filter(Company.created_at >= seven_days_ago).scalar() or 0
        new_30d = db.query(func.count(Company.id)).filter(Company.created_at >= thirty_days_ago).scalar() or 0

        total_projects = db.query(func.count(Project.id)).filter(Project.is_active == True).scalar() or 0
        total_issues = db.query(func.count(Issue.id)).filter(Issue.is_deleted == False).scalar() or 0

        # Company-wise activity table
        companies = db.query(Company).order_by(Company.name.asc()).all()
        activity_items: list[CompanyActivityItem] = []

        for c in companies:
            proj_count = db.query(func.count(Project.id)).filter(
                Project.company_id == c.id, Project.is_active == True
            ).scalar() or 0

            open_count = db.query(func.count(Issue.id)).join(Issue.status).filter(
                Issue.company_id == c.id, Issue.is_deleted == False, IssueStatus.name == "Open"
            ).scalar() or 0

            resolved_count = db.query(func.count(Issue.id)).join(Issue.status).filter(
                Issue.company_id == c.id, Issue.is_deleted == False, IssueStatus.name.in_(["Resolved", "Closed"])
            ).scalar() or 0

            crit_count = db.query(func.count(Issue.id)).join(Issue.priority).filter(
                Issue.company_id == c.id, Issue.is_deleted == False, IssuePriority.name == "Critical"
            ).scalar() or 0

            tot_issues = db.query(func.count(Issue.id)).filter(
                Issue.company_id == c.id, Issue.is_deleted == False
            ).scalar() or 0

            activity_items.append(CompanyActivityItem(
                company_id=c.id,
                company_name=c.name,
                is_active=c.is_active,
                projects_count=proj_count,
                open_issues=open_count,
                resolved_issues=resolved_count,
                critical_issues=crit_count,
                total_issues=tot_issues,
                created_at=c.created_at,
            ))

        return PlatformDashboardResponse(
            total_companies=total_companies,
            active_companies=active_companies,
            inactive_companies=inactive_companies,
            new_companies_last_7_days=new_7d,
            new_companies_last_30_days=new_30d,
            total_platform_projects=total_projects,
            total_platform_issues=total_issues,
            companies_activity=activity_items,
        )

    def get_platform_analytics(
        self, db: Session, company_id: Optional[int] = None, days: int = 30
    ) -> PlatformAnalyticsResponse:
        """
        Super Admin platform analytics.
        Strictly company-level metrics (Company -> Metrics).
        NO developer workload or individual rankings.
        Supports filtering by specific company or all companies and time range.
        """
        total_companies = db.query(func.count(Company.id)).scalar() or 0
        active_companies = db.query(func.count(Company.id)).filter(Company.is_active == True).scalar() or 0
        inactive_companies = total_companies - active_companies

        time_days = max(1, min(days, 365))
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=time_days)

        # 1. Growth trend over selected days (evenly spaced, always ending on today)
        num_intervals = 7 if time_days <= 7 else (6 if time_days <= 30 else 8)
        growth_points: list[CompanyGrowthPoint] = []
        day_offsets = sorted(list({int(round(i * (time_days - 1) / max(1, num_intervals - 1))) for i in range(num_intervals)}), reverse=True)
        for offset in day_offsets:
            d = now - timedelta(days=offset)
            count = db.query(func.count(Company.id)).filter(Company.created_at <= d).scalar() or 0
            growth_points.append(CompanyGrowthPoint(
                date=d.strftime("%Y-%m-%d"),
                companies_count=count,
            ))

        # 2. Company-wise defect metrics bounded by selected time window
        comp_query = db.query(Company)
        if company_id:
            comp_query = comp_query.filter(Company.id == company_id)
        target_companies = comp_query.order_by(Company.name.asc()).all()

        company_metrics: list[CompanyDefectMetric] = []
        for c in target_companies:
            created_c = db.query(func.count(Issue.id)).filter(
                Issue.company_id == c.id, Issue.is_deleted == False, Issue.created_at >= start_date
            ).scalar() or 0

            resolved_c = db.query(func.count(Issue.id)).join(Issue.status).filter(
                Issue.company_id == c.id, Issue.is_deleted == False,
                IssueStatus.name.in_(["Resolved", "Closed"]),
                Issue.updated_at >= start_date
            ).scalar() or 0

            open_c = db.query(func.count(Issue.id)).join(Issue.status).filter(
                Issue.company_id == c.id, Issue.is_deleted == False,
                IssueStatus.name.notin_(["Resolved", "Closed"]),
                Issue.created_at >= start_date
            ).scalar() or 0

            critical_c = db.query(func.count(Issue.id)).join(Issue.priority).join(Issue.status).filter(
                Issue.company_id == c.id, Issue.is_deleted == False,
                IssuePriority.name == "Critical",
                IssueStatus.name.notin_(["Resolved", "Closed"]),
                Issue.created_at >= start_date
            ).scalar() or 0

            # Compute average resolution time in hours for resolved defects in this period
            resolved_issues_objs = db.query(Issue).join(Issue.status).filter(
                Issue.company_id == c.id,
                Issue.is_deleted == False,
                IssueStatus.name.in_(["Resolved", "Closed"]),
                Issue.updated_at >= start_date
            ).all()

            durations = []
            for iss in resolved_issues_objs:
                if iss.updated_at and iss.created_at and iss.updated_at > iss.created_at:
                    durations.append((iss.updated_at - iss.created_at).total_seconds() / 3600.0)
            avg_hours = round(sum(durations) / len(durations), 1) if durations else 0.0

            company_metrics.append(CompanyDefectMetric(
                company_id=c.id,
                company_name=c.name,
                defects_created=created_c,
                defects_resolved=resolved_c,
                open_defects=open_c,
                critical_defects=critical_c,
                avg_resolution_hours=avg_hours,
            ))

        return PlatformAnalyticsResponse(
            total_companies=total_companies,
            active_companies=active_companies,
            inactive_companies=inactive_companies,
            growth_trend=growth_points,
            company_metrics=company_metrics,
        )

    # ── Customization Requests ──

    def list_customization_requests(
        self, db: Session, status_filter: str | None = None
    ) -> list[CustomizationRequestResponse]:
        query = db.query(CustomizationRequest).options(
            joinedload(CustomizationRequest.company),
            joinedload(CustomizationRequest.requester),
            joinedload(CustomizationRequest.reviewer),
            joinedload(CustomizationRequest.linked_issue).joinedload(Issue.status)
        )
        if status_filter and status_filter.strip():
            query = query.filter(CustomizationRequest.status == status_filter.strip())

        requests = query.order_by(CustomizationRequest.created_at.desc()).all()
        results = []
        for r in requests:
            impl_status = r.linked_issue.status.name if r.linked_issue and r.linked_issue.status else r.status
            linked_key = r.linked_issue.issue_key if r.linked_issue else None
            res_notes = r.linked_issue.resolution if r.linked_issue else None
            results.append(CustomizationRequestResponse(
                id=r.id,
                company_id=r.company_id,
                company_name=r.company.name if r.company else "Unknown",
                requester_id=r.requester_id,
                requester_name=r.requester.full_name if r.requester else "Unknown",
                title=r.title,
                description=r.description,
                request_type=getattr(r, 'request_type', 'Feature') or 'Feature',
                category=r.category,
                requested_behavior=r.requested_behavior,
                status=r.status,
                super_admin_notes=r.super_admin_notes,
                reviewed_by_id=r.reviewed_by_id,
                reviewer_name=r.reviewer.full_name if r.reviewer else None,
                reviewed_at=r.reviewed_at,
                linked_issue_id=r.linked_issue_id,
                linked_issue_key=linked_key,
                implementation_status=impl_status,
                resolution=res_notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
            ))
        return results

    def review_customization_request(
        self, db: Session, request_id: int, review_data: CustomizationRequestReview, current_user: User
    ) -> CustomizationRequestResponse:
        req = db.query(CustomizationRequest).options(
            joinedload(CustomizationRequest.company),
            joinedload(CustomizationRequest.requester),
            joinedload(CustomizationRequest.linked_issue).joinedload(Issue.status)
        ).filter(CustomizationRequest.id == request_id).first()

        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customization request not found")

        old_status = req.status
        req.status = review_data.status
        if review_data.super_admin_notes is not None:
            req.super_admin_notes = review_data.super_admin_notes
        req.reviewed_by_id = current_user.id
        req.reviewed_at = datetime.now(timezone.utc)

        db.add(CompanyAuditLog(
            company_id=req.company_id,
            user_id=current_user.id,
            action="CUSTOMIZATION_REQUEST_REVIEWED",
            entity_type="CUSTOMIZATION_REQUEST",
            entity_id=req.id,
            old_value={"status": old_status},
            new_value={"status": req.status, "notes": req.super_admin_notes},
        ))

        db.commit()
        db.refresh(req)

        impl_status = req.linked_issue.status.name if req.linked_issue and req.linked_issue.status else req.status
        linked_key = req.linked_issue.issue_key if req.linked_issue else None
        res_notes = req.linked_issue.resolution if req.linked_issue else None

        return CustomizationRequestResponse(
            id=req.id,
            company_id=req.company_id,
            company_name=req.company.name if req.company else "Unknown",
            requester_id=req.requester_id,
            requester_name=req.requester.full_name if req.requester else "Unknown",
            title=req.title,
            description=req.description,
            request_type=getattr(req, 'request_type', 'Feature') or 'Feature',
            category=req.category,
            requested_behavior=req.requested_behavior,
            status=req.status,
            super_admin_notes=req.super_admin_notes,
            reviewed_by_id=req.reviewed_by_id,
            reviewer_name=current_user.full_name,
            reviewed_at=req.reviewed_at,
            linked_issue_id=req.linked_issue_id,
            linked_issue_key=linked_key,
            implementation_status=impl_status,
            resolution=res_notes,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )



super_admin_service = SuperAdminService()


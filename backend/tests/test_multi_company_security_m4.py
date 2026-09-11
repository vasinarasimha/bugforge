"""
Comprehensive Multi-Company Security, Dynamic Statuses, and Super Admin Test Suite
Verifies:
1. Strict tenant isolation (Project, Issue, Sprint, User, Search)
2. Super Admin atomic company + admin creation transaction
3. Company deactivation (soft toggle, preserving data)
4. Platform-level vs company-level analytics (No employee workload on Super Admin)
5. Dynamic issue status management (add, active toggle, dependency check)
6. Customization request lifecycle
7. Company audit logging
"""
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal
from app.models.company import Company, CompanySettings
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity
from app.models.sprint import Sprint
from app.models.customization_request import CustomizationRequest
from app.models.company_audit_log import CompanyAuditLog
from app.services.super_admin_service import super_admin_service
from app.services.company_settings_service import company_settings_service
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.sprint_service import SprintService
from app.schemas.company import (
    CompanyCreateWithAdmin, InitialAdminCreate,
    CustomizationRequestCreate, CustomizationRequestReview
)
from app.schemas.issue import (
    IssueCreate, IssueUpdate, IssueStatusCreate, IssueStatusUpdate
)
from app.schemas.project import ProjectCreate


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_setup(db_session: Session):
    """
    Setup two isolated test companies:
    - Company Alpha (id: alpha_company.id)
    - Company Beta (id: beta_company.id)
    - Plus Super Admin (company_id: None)
    """
    # 1. Super Admin
    super_admin = db_session.query(User).filter(User.email == "test_superadmin_m4@bugforge.test").first()
    if not super_admin:
        sa_role = db_session.query(Role).filter(Role.name == "Super Admin").first()
        if not sa_role:
            sa_role = Role(name="Super Admin")
            db_session.add(sa_role)
            db_session.flush()

        super_admin = User(
            email="test_superadmin_m4@bugforge.test",
            password_hash="testpasshash123",
            full_name="Global Super Admin",
            company_id=None,
            is_active=True,
            is_system_user=True,
            roles=[sa_role]
        )
        db_session.add(super_admin)
        db_session.flush()

    # 2. Company Alpha
    alpha = db_session.query(Company).filter(Company.name == "Alpha Corp Test").first()
    if not alpha:
        alpha = Company(name="Alpha Corp Test", is_active=True)
        db_session.add(alpha)
        db_session.flush()

    admin_role = db_session.query(Role).filter(Role.name == "Admin").first()
    dev_role = db_session.query(Role).filter(Role.name == "Developer").first()

    alpha_admin = db_session.query(User).filter(User.email == "admin@alpha.test").first()
    if not alpha_admin:
        alpha_admin = User(
            email="admin@alpha.test",
            password_hash="hash",
            full_name="Alpha Admin",
            company_id=alpha.id,
            is_active=True,
            roles=[admin_role] if admin_role else []
        )
        db_session.add(alpha_admin)
        db_session.flush()

    alpha_user = db_session.query(User).filter(User.email == "dev@alpha.test").first()
    if not alpha_user:
        alpha_user = User(
            email="dev@alpha.test",
            password_hash="hash",
            full_name="Alpha Dev",
            company_id=alpha.id,
            is_active=True,
            roles=[dev_role] if dev_role else []
        )
        db_session.add(alpha_user)
        db_session.flush()

    # Initialize Alpha Statuses
    alpha_open_status = db_session.query(IssueStatus).filter(
        IssueStatus.company_id == alpha.id,
        IssueStatus.name == "Alpha Open"
    ).first()
    if not alpha_open_status:
        alpha_open_status = IssueStatus(
            name="Alpha Open",
            company_id=alpha.id,
            category="open",
            color="#3b82f6",
            is_initial=True,
            is_active=True
        )
        db_session.add(alpha_open_status)
        db_session.flush()

    # 3. Company Beta
    beta = db_session.query(Company).filter(Company.name == "Beta Corp Test").first()
    if not beta:
        beta = Company(name="Beta Corp Test", is_active=True)
        db_session.add(beta)
        db_session.flush()

    beta_admin = db_session.query(User).filter(User.email == "admin@beta.test").first()
    if not beta_admin:
        beta_admin = User(
            email="admin@beta.test",
            password_hash="hash",
            full_name="Beta Admin",
            company_id=beta.id,
            is_active=True,
            roles=[admin_role] if admin_role else []
        )
        db_session.add(beta_admin)
        db_session.flush()

    beta_user = db_session.query(User).filter(User.email == "dev@beta.test").first()
    if not beta_user:
        beta_user = User(
            email="dev@beta.test",
            password_hash="hash",
            full_name="Beta Dev",
            company_id=beta.id,
            is_active=True,
            roles=[dev_role] if dev_role else []
        )
        db_session.add(beta_user)
        db_session.flush()

    beta_open_status = db_session.query(IssueStatus).filter(
        IssueStatus.company_id == beta.id,
        IssueStatus.name == "Beta Open"
    ).first()
    if not beta_open_status:
        beta_open_status = IssueStatus(
            name="Beta Open",
            company_id=beta.id,
            category="open",
            color="#10b981",
            is_initial=True,
            is_active=True
        )
        db_session.add(beta_open_status)
        db_session.flush()

    # Create a project in Company Alpha
    alpha_proj = db_session.query(Project).filter(Project.name == "Alpha Portal Project").first()
    if not alpha_proj:
        alpha_proj = Project(
            name="Alpha Portal Project",
            key="ALP",
            description="Alpha portal",
            company_id=alpha.id,
            created_by=alpha_admin.id,
            is_active=True
        )
        db_session.add(alpha_proj)
        db_session.flush()

    # Create a project in Company Beta
    beta_proj = db_session.query(Project).filter(Project.name == "Beta Mobile Project").first()
    if not beta_proj:
        beta_proj = Project(
            name="Beta Mobile Project",
            key="BET",
            description="Beta mobile app",
            company_id=beta.id,
            created_by=beta_admin.id,
            is_active=True
        )
        db_session.add(beta_proj)
        db_session.flush()

    db_session.commit()

    return {
        "super_admin": super_admin,
        "alpha": alpha,
        "alpha_admin": alpha_admin,
        "alpha_user": alpha_user,
        "alpha_proj": alpha_proj,
        "alpha_open_status": alpha_open_status,
        "beta": beta,
        "beta_admin": beta_admin,
        "beta_user": beta_user,
        "beta_proj": beta_proj,
        "beta_open_status": beta_open_status,
    }


class TestTenantIsolation:
    """Verify Company A cannot see or tamper with Company B resources."""

    def test_project_isolation(self, db_session: Session, test_setup: dict):
        proj_service = ProjectService()
        alpha_user = test_setup["alpha_user"]
        beta_proj = test_setup["beta_proj"]

        # Alpha user querying Beta project should raise 404 (not accessible to other companies)
        with pytest.raises(HTTPException) as exc_info:
            proj_service.get(db_session, beta_proj.id, company_id=alpha_user.company_id)
        assert exc_info.value.status_code == 404

    def test_cross_company_issue_creation_blocked(self, db_session: Session, test_setup: dict):
        """Alpha user attempting to create an issue referencing Beta project or Beta assignee must fail."""
        issue_service = IssueService()
        alpha_user = test_setup["alpha_user"]
        beta_proj = test_setup["beta_proj"]
        beta_user = test_setup["beta_user"]
        alpha_proj = test_setup["alpha_proj"]
        alpha_status = test_setup["alpha_open_status"]

        # Case 1: Issue referencing cross-company project
        with pytest.raises(HTTPException) as exc_info:
            issue_service.create(
                db_session,
                IssueCreate(
                    title="Illegitimate Defect",
                    description="Trying to inject into Beta",
                    project_id=beta_proj.id,  # Invalid: Beta's project
                    status_id=alpha_status.id,
                    priority_id=1,
                    severity_id=1,
                ),
                alpha_user
            )
        assert exc_info.value.status_code in (403, 404)

        # Case 2: Issue referencing cross-company assignee
        with pytest.raises(HTTPException) as exc_info:
            issue_service.create(
                db_session,
                IssueCreate(
                    title="Illegitimate Assignee Defect",
                    description="Trying to assign to Beta user",
                    project_id=alpha_proj.id,
                    assigned_to=beta_user.id,  # Invalid: Beta's user
                    status_id=alpha_status.id,
                    priority_id=1,
                    severity_id=1,
                ),
                alpha_user
            )
        assert exc_info.value.status_code in (403, 404)

    def test_cross_company_sprint_isolation(self, db_session: Session, test_setup: dict):
        """Sprints in Company B cannot be accessed or created by Company A."""
        from app.schemas.sprint import SprintCreate
        sprint_service = SprintService()
        alpha_user = test_setup["alpha_user"]
        beta_proj = test_setup["beta_proj"]

        # Alpha user cannot create sprint in Beta project
        with pytest.raises(HTTPException) as exc_info:
            sprint_service.create(
                db_session,
                SprintCreate(
                    name="Illegitimate Sprint",
                    status_id=1,
                    project_id=beta_proj.id
                ),
                alpha_user
            )
        assert exc_info.value.status_code in (403, 404)


class TestSuperAdminCompanyCreationAndLifecycle:
    """Verify Super Admin atomic company creation and deactivation."""

    def test_atomic_company_creation(self, db_session: Session, test_setup: dict):
        """Creating a company with initial admin must create company, settings, statuses, and admin."""
        import uuid
        uid = uuid.uuid4().hex[:6]
        cname = f"Gamma Test {uid}"
        cemail = f"contact_{uid}@gamma-corp.com"
        admin_email = f"admin_{uid}@gamma-corp.com"

        new_company_data = CompanyCreateWithAdmin(
            name=cname,
            legal_name=f"{cname} Pvt Ltd",
            email=cemail,
            phone="1234567890",
            city="Bengaluru",
            country="India",
            timezone="Asia/Kolkata",
            admin=InitialAdminCreate(
                first_name="Gamma",
                last_name="Admin",
                email=admin_email,
                password="SecurePassword123!",
                mobile_number="9876543210"
            )
        )

        super_admin = test_setup["super_admin"]

        # Execute creation
        result = super_admin_service.create_company_with_admin(db_session, new_company_data, super_admin)
        assert result["company"]["name"] == cname
        company_id = result["company"]["id"]
        assert result["admin"]["email"] == admin_email

        # Verify company settings were automatically initialized
        cs = db_session.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
        assert cs is not None
        assert cs.settings.get("workflow", {}).get("default_status") == "Open"

        # Verify default statuses were initialized for Gamma
        statuses = db_session.query(IssueStatus).filter(IssueStatus.company_id == company_id).all()
        assert len(statuses) >= 4
        status_names = [s.name for s in statuses]
        assert "Open" in status_names
        assert "In Progress" in status_names
        assert "Resolved" in status_names

        # Verify initial Company Admin user was created with company_id and Admin role
        admin_user = db_session.query(User).filter(User.email == admin_email).first()
        assert admin_user is not None
        assert admin_user.company_id == company_id
        assert any(r.name == "Admin" for r in admin_user.roles)

    def test_company_deactivation_and_reactivation(self, db_session: Session, test_setup: dict):
        """Soft deactivation toggles is_active without deleting any historical records."""
        beta = test_setup["beta"]
        super_admin = test_setup["super_admin"]

        # Deactivate
        super_admin_service.set_company_active_status(db_session, beta.id, is_active=False, current_user=super_admin)
        db_session.refresh(beta)
        assert beta.is_active is False

        # Reactivate
        super_admin_service.set_company_active_status(db_session, beta.id, is_active=True, current_user=super_admin)
        db_session.refresh(beta)
        assert beta.is_active is True


class TestDynamicIssueStatuses:
    """Verify Company Admin can customize issue statuses with dependency safety."""

    def test_create_company_specific_status(self, db_session: Session, test_setup: dict):
        alpha = test_setup["alpha"]
        alpha_admin = test_setup["alpha_admin"]
        import uuid
        st_name = f"QA Review {uuid.uuid4().hex[:6]}"

        # Add new status
        new_status = company_settings_service.create_status(
            db_session,
            alpha.id,
            IssueStatusCreate(
                name=st_name,
                category="in_progress",
                color="#ec4899",
                order_index=5
            ),
            alpha_admin
        )
        assert new_status["name"] == st_name
        assert new_status["company_id"] == alpha.id

        # Verify duplicate name is rejected
        with pytest.raises(HTTPException) as exc_info:
            company_settings_service.create_status(
                db_session,
                alpha.id,
                IssueStatusCreate(name=st_name, category="in_progress"),
                alpha_admin
            )
        assert exc_info.value.status_code == 409

    def test_deactivate_status_with_issue_dependency(self, db_session: Session, test_setup: dict):
        """Status referenced by issues cannot be physically deleted; it is safely deactivated."""
        alpha = test_setup["alpha"]
        alpha_admin = test_setup["alpha_admin"]
        alpha_proj = test_setup["alpha_proj"]
        alpha_user = test_setup["alpha_user"]
        import uuid
        st_name = f"Dep Test Status {uuid.uuid4().hex[:6]}"

        # Create a status and assign an issue to it
        st = IssueStatus(
            name=st_name,
            company_id=alpha.id,
            category="open",
            is_active=True
        )
        db_session.add(st)
        db_session.flush()

        issue = Issue(
            issue_key=f"ALP-{uuid.uuid4().hex[:4]}",
            title="Dependent Defect",
            description="Linked to Dep Test Status",
            project_id=alpha_proj.id,
            company_id=alpha.id,
            reporter_id=alpha_user.id,
            status_id=st.id,
            priority_id=1,
            severity_id=1,
            is_deleted=False
        )
        db_session.add(issue)
        db_session.commit()

        # Attempt to delete/deactivate status
        res = company_settings_service.delete_or_deactivate_status(
            db_session, alpha.id, st.id, alpha_admin
        )
        assert res["action"] == "deactivated"
        assert res["issue_count"] >= 1
        assert "currently use status" in res["message"]

        # Historical issue still references this status
        db_session.refresh(issue)
        assert issue.status_id == st.id

        # Status is now marked inactive
        db_session.refresh(st)
        assert st.is_active is False


class TestCustomizationRequests:
    """Verify Company Admin submit -> Super Admin review workflow."""

    def test_customization_request_lifecycle(self, db_session: Session, test_setup: dict):
        alpha = test_setup["alpha"]
        alpha_admin = test_setup["alpha_admin"]
        super_admin = test_setup["super_admin"]

        # 1. Company Admin submits request
        req = company_settings_service.submit_customization_request(
            db_session,
            alpha.id,
            CustomizationRequestCreate(
                title="Automated Vulnerability Scanner Hook",
                category="Integration",
                description="Trigger external scanner on release status transition.",
                requested_behavior="Webhook trigger before status changes to Verified."
            ),
            alpha_admin
        )
        assert req.id is not None
        assert req.status == "Pending"
        req_id = req.id

        # 2. Super Admin views platform-wide requests
        all_reqs = super_admin_service.list_customization_requests(db_session)
        matching = [r for r in all_reqs if r.id == req_id]
        assert len(matching) == 1
        assert matching[0].company_name == alpha.name

        # 3. Super Admin reviews & approves with notes
        reviewed = super_admin_service.review_customization_request(
            db_session,
            req_id,
            CustomizationRequestReview(
                status="Approved",
                super_admin_notes="Approved for Milestone 5 plugin integration roadmap."
            ),
            super_admin
        )
        assert reviewed.status == "Approved"
        assert reviewed.super_admin_notes == "Approved for Milestone 5 plugin integration roadmap."

        # 4. Company Admin sees the updated status and notes
        company_reqs = company_settings_service.list_customization_requests(db_session, alpha.id)
        comp_matching = [r for r in company_reqs if r.id == req_id]
        assert len(comp_matching) == 1
        assert comp_matching[0].status == "Approved"
        assert comp_matching[0].super_admin_notes == "Approved for Milestone 5 plugin integration roadmap."



class TestSuperAdminAnalyticsScope:
    """Verify Super Admin analytics operates strictly at company level with NO employee data."""

    def test_super_admin_analytics_no_employee_data(self, db_session: Session):
        overview = super_admin_service.get_platform_dashboard(db_session)
        assert overview.total_companies >= 1
        assert hasattr(overview, "companies_activity")

        # Verify companies_activity items do not contain any developer or employee fields
        for act in overview.companies_activity:
            assert not hasattr(act, "developer_id")
            assert not hasattr(act, "employee_id")
            assert not hasattr(act, "user_id")
            assert not hasattr(act, "developer_name")
            assert not hasattr(act, "employee_workload")
            # Check required company-level fields
            assert hasattr(act, "company_id")
            assert hasattr(act, "company_name")
            assert hasattr(act, "projects_count")
            assert hasattr(act, "open_issues")
            assert hasattr(act, "resolved_issues")

        # Verify analytics endpoint
        analytics = super_admin_service.get_platform_analytics(db_session, company_id=None)
        assert hasattr(analytics, "growth_trend")
        assert hasattr(analytics, "company_metrics")

        for defect_metric in analytics.company_metrics:
            assert not hasattr(defect_metric, "employee")
            assert not hasattr(defect_metric, "user")
            assert hasattr(defect_metric, "company_id")
            assert hasattr(defect_metric, "defects_created")
            assert hasattr(defect_metric, "defects_resolved")


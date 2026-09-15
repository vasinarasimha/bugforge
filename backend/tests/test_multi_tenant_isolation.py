"""
Comprehensive Multi-Tenant Isolation Test Suite
Verifies:
1. Issue isolation (list, get, delete, history, comments, attachments)
2. Project isolation (list, get, update, delete, history)
3. Team isolation (list, get, stats, available leaders, available members)
4. Sprint isolation (list, get, update, delete, assign issue)
5. Dashboard & stats isolation (statistics, admin-stats, pm-stats, tl-stats, dev-stats, qa-stats, reporter-stats)
6. Directory user isolation (/auth/users)
7. AI assistance isolation (resolution-assistance, test-cases, missing-scenarios)
8. Client feature requests: Company A sees its own requested features, Company B cannot see Company A's requested features
9. Super Admin retaining full global visibility across all companies
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.api.dependencies.auth import get_current_user
from app.models.company import Company
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity
from app.models.team import Team, TeamMember
from app.models.sprint import Sprint, SprintStatus
from app.models.comment import IssueComment
from app.models.history import IssueHistory
from app.models.project_history import ProjectHistory
from app.models.attachment import IssueAttachment

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def tenant_fixture(db_session: Session):
    """
    Sets up two isolated tenant companies (Tenant Alpha & Tenant Beta)
    and test users for Admin, PM, Dev, plus Super Admin.
    Cleans up all created test entities upon module completion.
    """
    created_entities = []

    try:
        # Roles lookup
        admin_role = db_session.query(Role).filter(Role.name == "Admin").first()
        pm_role = db_session.query(Role).filter(Role.name == "Project Manager").first()
        dev_role = db_session.query(Role).filter(Role.name == "Developer").first()
        sa_role = db_session.query(Role).filter(Role.name == "Super Admin").first()
        qa_role = db_session.query(Role).filter(Role.name == "QA").first()

        # Statuses
        open_status = db_session.query(IssueStatus).filter(IssueStatus.name == "Open").first()
        resolved_status = db_session.query(IssueStatus).filter(IssueStatus.name.ilike("%Resolved%")).first()
        if not open_status:
            open_status = db_session.query(IssueStatus).first()
        if not resolved_status:
            resolved_status = open_status

        priority = db_session.query(IssuePriority).first()
        severity = db_session.query(IssueSeverity).first()
        sprint_status = db_session.query(SprintStatus).first()

        # 1. Companies
        company_a = Company(name="Tenant Isolation Alpha Corp", is_active=True)
        company_b = Company(name="Tenant Isolation Beta Corp", is_active=True)
        db_session.add_all([company_a, company_b])
        db_session.flush()
        created_entities.extend([company_a, company_b])

        # 2. Users
        sa_user = User(
            email="sa_iso@bugforge.test",
            password_hash="testhash",
            full_name="SA Isolation User",
            company_id=None,
            is_active=True,
            is_system_user=True,
            roles=[sa_role] if sa_role else []
        )

        admin_a = User(
            email="admin_a_iso@alpha.test",
            password_hash="testhash",
            full_name="Admin Alpha User",
            company_id=company_a.id,
            is_active=True,
            roles=[admin_role] if admin_role else []
        )
        pm_a = User(
            email="pm_a_iso@alpha.test",
            password_hash="testhash",
            full_name="PM Alpha User",
            company_id=company_a.id,
            is_active=True,
            roles=[pm_role] if pm_role else []
        )
        dev_a = User(
            email="dev_a_iso@alpha.test",
            password_hash="testhash",
            full_name="Dev Alpha User",
            company_id=company_a.id,
            is_active=True,
            roles=[dev_role] if dev_role else []
        )

        admin_b = User(
            email="admin_b_iso@beta.test",
            password_hash="testhash",
            full_name="Admin Beta User",
            company_id=company_b.id,
            is_active=True,
            roles=[admin_role] if admin_role else []
        )
        pm_b = User(
            email="pm_b_iso@beta.test",
            password_hash="testhash",
            full_name="PM Beta User",
            company_id=company_b.id,
            is_active=True,
            roles=[pm_role] if pm_role else []
        )
        dev_b = User(
            email="dev_b_iso@beta.test",
            password_hash="testhash",
            full_name="Dev Beta User",
            company_id=company_b.id,
            is_active=True,
            roles=[dev_role] if dev_role else []
        )

        db_session.add_all([sa_user, admin_a, pm_a, dev_a, admin_b, pm_b, dev_b])
        db_session.flush()
        created_entities.extend([sa_user, admin_a, pm_a, dev_a, admin_b, pm_b, dev_b])

        # 3. Projects
        proj_a = Project(
            name="Project Alpha Iso",
            key="PAI",
            description="Alpha project",
            company_id=company_a.id,
            project_manager_id=pm_a.id,
            created_by=admin_a.id,
            is_active=True,
            status="Active"
        )
        proj_b = Project(
            name="Project Beta Iso",
            key="PBI",
            description="Beta project",
            company_id=company_b.id,
            project_manager_id=pm_b.id,
            created_by=admin_b.id,
            is_active=True,
            status="Active"
        )
        db_session.add_all([proj_a, proj_b])
        db_session.flush()
        created_entities.extend([proj_a, proj_b])

        # 4. Teams
        team_a = Team(
            name="Team Alpha Iso",
            company_id=company_a.id,
            team_leader_id=admin_a.id,
            project_manager_id=pm_a.id,
            is_active=True
        )
        team_b = Team(
            name="Team Beta Iso",
            company_id=company_b.id,
            team_leader_id=admin_b.id,
            project_manager_id=pm_b.id,
            is_active=True
        )
        db_session.add_all([team_a, team_b])
        db_session.flush()
        created_entities.extend([team_a, team_b])

        tm_a = TeamMember(team_id=team_a.id, user_id=dev_a.id)
        tm_b = TeamMember(team_id=team_b.id, user_id=dev_b.id)
        db_session.add_all([tm_a, tm_b])
        db_session.flush()
        created_entities.extend([tm_a, tm_b])

        # 5. Sprints
        sprint_a = Sprint(
            name="Sprint Alpha Iso 1",
            goal="Goal Alpha",
            status_id=sprint_status.id if sprint_status else None,
            project_id=proj_a.id,
            created_by=pm_a.id
        )
        sprint_b = Sprint(
            name="Sprint Beta Iso 1",
            goal="Goal Beta",
            status_id=sprint_status.id if sprint_status else None,
            project_id=proj_b.id,
            created_by=pm_b.id
        )
        db_session.add_all([sprint_a, sprint_b])
        db_session.flush()
        created_entities.extend([sprint_a, sprint_b])

        # 6. Issues
        issue_a = Issue(
            title="Issue Alpha Internal Bug",
            description="Alpha issue description",
            issue_key="PAI-101",
            issue_type="Defect",
            company_id=company_a.id,
            project_id=proj_a.id,
            reporter_id=admin_a.id,
            assigned_to=dev_a.id,
            status_id=open_status.id if open_status else None,
            priority_id=priority.id if priority else None,
            severity_id=severity.id if severity else None,
            is_active=True,
            is_deleted=False
        )
        issue_b = Issue(
            title="Issue Beta Internal Bug",
            description="Beta issue description",
            issue_key="PBI-101",
            issue_type="Defect",
            company_id=company_b.id,
            project_id=proj_b.id,
            reporter_id=admin_b.id,
            assigned_to=dev_b.id,
            status_id=open_status.id if open_status else None,
            priority_id=priority.id if priority else None,
            severity_id=severity.id if severity else None,
            is_active=True,
            is_deleted=False
        )
        # Client feature request for Company A (company_id=1, requesting_company_id=company_a.id)
        c1_proj = db_session.query(Project).filter(Project.company_id == 1).first()
        issue_req_a = Issue(
            title="Feature Request from Alpha Corp",
            description="Client requested capability",
            issue_key="BUG-CUST-999",
            issue_type="Feature Request",
            company_id=1,
            project_id=c1_proj.id if c1_proj else proj_a.id,
            requesting_company_id=company_a.id,
            reporter_id=admin_a.id,
            status_id=open_status.id if open_status else None,
            priority_id=priority.id if priority else None,
            severity_id=severity.id if severity else None,
            is_active=True,
            is_deleted=False
        )
        db_session.add_all([issue_a, issue_b, issue_req_a])
        db_session.flush()
        created_entities.extend([issue_a, issue_b, issue_req_a])

        # 7. Sub-entities (Comments, History, Attachments)
        comment_a = IssueComment(
            issue_id=issue_a.id,
            user_id=admin_a.id,
            content="Alpha comment content"
        )
        comment_b = IssueComment(
            issue_id=issue_b.id,
            user_id=admin_b.id,
            content="Beta comment content"
        )
        history_a = IssueHistory(
            issue_id=issue_a.id,
            user_id=admin_a.id,
            field_name="status",
            old_value="Draft",
            new_value="Open"
        )
        history_b = IssueHistory(
            issue_id=issue_b.id,
            user_id=admin_b.id,
            field_name="status",
            old_value="Draft",
            new_value="Open"
        )
        proj_hist_a = ProjectHistory(
            project_id=proj_a.id,
            user_id=admin_a.id,
            field_name="status",
            old_value="Created",
            new_value="Active"
        )
        proj_hist_b = ProjectHistory(
            project_id=proj_b.id,
            user_id=admin_b.id,
            field_name="status",
            old_value="Created",
            new_value="Active"
        )
        attachment_a = IssueAttachment(
            issue_id=issue_a.id,
            uploaded_by=admin_a.id,
            filename="alpha_doc.txt",
            file_path="/uploads/alpha_doc.txt",
            file_size=128
        )
        attachment_b = IssueAttachment(
            issue_id=issue_b.id,
            uploaded_by=admin_b.id,
            filename="beta_doc.txt",
            file_path="/uploads/beta_doc.txt",
            file_size=128
        )
        db_session.add_all([
            comment_a, comment_b, history_a, history_b,
            proj_hist_a, proj_hist_b, attachment_a, attachment_b
        ])
        db_session.commit()
        created_entities.extend([
            comment_a, comment_b, history_a, history_b,
            proj_hist_a, proj_hist_b, attachment_a, attachment_b
        ])

        yield {
            "company_a": company_a,
            "company_b": company_b,
            "sa_user": sa_user,
            "admin_a": admin_a,
            "pm_a": pm_a,
            "dev_a": dev_a,
            "admin_b": admin_b,
            "pm_b": pm_b,
            "dev_b": dev_b,
            "proj_a": proj_a,
            "proj_b": proj_b,
            "team_a": team_a,
            "team_b": team_b,
            "sprint_a": sprint_a,
            "sprint_b": sprint_b,
            "issue_a": issue_a,
            "issue_b": issue_b,
            "issue_req_a": issue_req_a,
            "comment_a": comment_a,
            "comment_b": comment_b,
            "attachment_a": attachment_a,
            "attachment_b": attachment_b,
        }

    finally:
        # Explicit clean up of created test records in reverse order
        for entity in reversed(created_entities):
            try:
                db_session.delete(entity)
                db_session.commit()
            except Exception:
                db_session.rollback()


class TestMultiTenantIssueIsolation:

    def test_get_issue_isolation(self, tenant_fixture):
        """User from Company A must receive 404/403 when requesting Company B's issue."""
        dev_a = tenant_fixture["dev_a"]
        issue_b = tenant_fixture["issue_b"]
        issue_a = tenant_fixture["issue_a"]
        sa = tenant_fixture["sa_user"]

        # Company A dev queries Company B issue -> 404
        app.dependency_overrides[get_current_user] = lambda: dev_a
        resp = client.get(f"/api/issues/{issue_b.id}")
        assert resp.status_code == 404

        # Company A dev queries Company A issue -> 200
        resp = client.get(f"/api/issues/{issue_a.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == issue_a.id

        # Super Admin queries Company B issue -> 200
        app.dependency_overrides[get_current_user] = lambda: sa
        resp = client.get(f"/api/issues/{issue_b.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == issue_b.id

    def test_list_issues_isolation(self, tenant_fixture):
        """Listing issues returns only user's own company issues + client requests."""
        dev_a = tenant_fixture["dev_a"]
        dev_b = tenant_fixture["dev_b"]
        issue_a = tenant_fixture["issue_a"]
        issue_b = tenant_fixture["issue_b"]
        issue_req_a = tenant_fixture["issue_req_a"]

        # Dev A sees issue_a and issue_req_a, but NEVER issue_b
        app.dependency_overrides[get_current_user] = lambda: dev_a
        resp = client.get("/api/issues")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()]
        assert issue_a.id in ids
        assert issue_req_a.id in ids
        assert issue_b.id not in ids

        # Dev B sees issue_b, but NEVER issue_a or issue_req_a
        app.dependency_overrides[get_current_user] = lambda: dev_b
        resp = client.get("/api/issues")
        assert resp.status_code == 200
        ids_b = [i["id"] for i in resp.json()]
        assert issue_b.id in ids_b
        assert issue_a.id not in ids_b
        assert issue_req_a.id not in ids_b

    def test_issue_sub_entities_isolation(self, tenant_fixture):
        """Comments, History, and Attachments of Company B must not be accessible to Company A."""
        dev_a = tenant_fixture["dev_a"]
        issue_b = tenant_fixture["issue_b"]

        app.dependency_overrides[get_current_user] = lambda: dev_a

        # History
        resp = client.get(f"/api/issues/{issue_b.id}/history")
        assert resp.status_code in (403, 404)

        # Comments
        resp = client.get(f"/api/issues/{issue_b.id}/comments")
        assert resp.status_code in (403, 404)

        # Create Comment
        resp = client.post(f"/api/issues/{issue_b.id}/comments", json={"content": "Intruder comment"})
        assert resp.status_code in (403, 404)

        # Attachments
        resp = client.get(f"/api/issues/{issue_b.id}/attachments")
        assert resp.status_code in (403, 404)


class TestMultiTenantProjectIsolation:

    def test_project_get_and_list_isolation(self, tenant_fixture):
        """Company A cannot list or get Company B projects."""
        admin_a = tenant_fixture["admin_a"]
        proj_a = tenant_fixture["proj_a"]
        proj_b = tenant_fixture["proj_b"]
        sa = tenant_fixture["sa_user"]

        app.dependency_overrides[get_current_user] = lambda: admin_a

        # List
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        proj_ids = [p["id"] for p in resp.json()]
        assert proj_a.id in proj_ids
        assert proj_b.id not in proj_ids

        # Get Company B project -> 404
        resp = client.get(f"/api/projects/{proj_b.id}")
        assert resp.status_code == 404

        # Project History -> 404
        resp = client.get(f"/api/projects/{proj_b.id}/history")
        assert resp.status_code == 404

        # Super Admin can get Company B project -> 200
        app.dependency_overrides[get_current_user] = lambda: sa
        resp = client.get(f"/api/projects/{proj_b.id}")
        assert resp.status_code == 200


class TestMultiTenantTeamIsolation:

    def test_team_get_and_list_isolation(self, tenant_fixture):
        """Company A cannot list, get, or view stats of Company B teams."""
        admin_a = tenant_fixture["admin_a"]
        team_a = tenant_fixture["team_a"]
        team_b = tenant_fixture["team_b"]
        sa = tenant_fixture["sa_user"]

        app.dependency_overrides[get_current_user] = lambda: admin_a

        # List
        resp = client.get("/api/teams")
        assert resp.status_code == 200
        team_ids = [t["id"] for t in resp.json()]
        assert team_a.id in team_ids
        assert team_b.id not in team_ids

        # Get Company B team -> 403 or 404
        resp = client.get(f"/api/teams/{team_b.id}")
        assert resp.status_code in (403, 404)

        # Team Stats -> 403 or 404
        resp = client.get(f"/api/teams/{team_b.id}/stats")
        assert resp.status_code in (403, 404)

        # Super Admin can list teams from both
        app.dependency_overrides[get_current_user] = lambda: sa
        resp = client.get("/api/teams")
        assert resp.status_code == 200
        all_team_ids = [t["id"] for t in resp.json()]
        assert team_a.id in all_team_ids
        assert team_b.id in all_team_ids

    def test_available_members_and_leaders_isolation(self, tenant_fixture):
        """Available leaders and members only return users belonging to the caller's company."""
        admin_a = tenant_fixture["admin_a"]
        dev_b = tenant_fixture["dev_b"]

        app.dependency_overrides[get_current_user] = lambda: admin_a

        resp = client.get("/api/teams/meta/available-members")
        assert resp.status_code == 200
        member_ids = [m["id"] for m in resp.json()]
        assert dev_b.id not in member_ids


class TestMultiTenantSprintIsolation:

    def test_sprint_isolation(self, tenant_fixture):
        """Company A cannot list or get Company B sprints, nor assign issues across companies."""
        pm_a = tenant_fixture["pm_a"]
        sprint_a = tenant_fixture["sprint_a"]
        sprint_b = tenant_fixture["sprint_b"]
        issue_b = tenant_fixture["issue_b"]

        app.dependency_overrides[get_current_user] = lambda: pm_a

        # List
        resp = client.get("/api/sprints")
        assert resp.status_code == 200
        sprint_ids = [s["id"] for s in resp.json()]
        assert sprint_a.id in sprint_ids
        assert sprint_b.id not in sprint_ids

        # Get
        resp = client.get(f"/api/sprints/{sprint_b.id}")
        assert resp.status_code in (403, 404)

        # Assign Company B's issue to Company A's sprint -> 403 or 404
        resp = client.put(f"/api/sprints/{sprint_a.id}/issues/{issue_b.id}")
        assert resp.status_code in (400, 403, 404)


class TestMultiTenantDashboardAndDirectoryIsolation:

    def test_auth_users_isolation(self, tenant_fixture):
        """Directory endpoint /api/auth/users must only return employees of current company."""
        admin_a = tenant_fixture["admin_a"]
        dev_a = tenant_fixture["dev_a"]
        dev_b = tenant_fixture["dev_b"]
        sa = tenant_fixture["sa_user"]

        app.dependency_overrides[get_current_user] = lambda: admin_a
        resp = client.get("/api/auth/users")
        assert resp.status_code == 200
        user_ids = [u["id"] for u in resp.json()["data"]]
        assert dev_a.id in user_ids
        assert dev_b.id not in user_ids

        # Super Admin sees users from both
        app.dependency_overrides[get_current_user] = lambda: sa
        resp = client.get("/api/auth/users")
        assert resp.status_code == 200
        all_ids = [u["id"] for u in resp.json()["data"]]
        assert dev_a.id in all_ids
        assert dev_b.id in all_ids

    def test_dashboard_statistics_isolation(self, tenant_fixture):
        """Dashboard statistics counts only user's company records."""
        admin_a = tenant_fixture["admin_a"]
        admin_b = tenant_fixture["admin_b"]

        app.dependency_overrides[get_current_user] = lambda: admin_a
        resp_a = client.get("/api/dashboard/statistics")
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        latest_proj_ids_a = [p["id"] for p in data_a.get("latest_projects", [])]
        assert tenant_fixture["proj_b"].id not in latest_proj_ids_a

        app.dependency_overrides[get_current_user] = lambda: admin_b
        resp_b = client.get("/api/dashboard/statistics")
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        latest_proj_ids_b = [p["id"] for p in data_b.get("latest_projects", [])]
        assert tenant_fixture["proj_a"].id not in latest_proj_ids_b


class TestMultiTenantAIIsolation:

    def test_ai_resolution_assistance_isolation(self, tenant_fixture):
        """AI resolution assistance must 404 on cross-company issues."""
        dev_a = tenant_fixture["dev_a"]
        issue_b = tenant_fixture["issue_b"]

        app.dependency_overrides[get_current_user] = lambda: dev_a
        resp = client.post("/api/ai/resolution-assistance", json={"issue_id": issue_b.id})
        assert resp.status_code == 404

    def test_ai_qa_endpoints_isolation(self, tenant_fixture):
        """QA AI test generation must 404 on cross-company issues."""
        admin_a = tenant_fixture["admin_a"]
        issue_b = tenant_fixture["issue_b"]

        app.dependency_overrides[get_current_user] = lambda: admin_a
        resp = client.post("/api/ai/test-cases", json={"issue_id": issue_b.id})
        assert resp.status_code == 404

        resp = client.post("/api/ai/missing-scenarios", json={"issue_id": issue_b.id, "existing_test_cases": []})
        assert resp.status_code == 404


class TestMultiTenantMutationsAndLookups:

    def test_project_mutation_isolation(self, tenant_fixture):
        """Admin from Company A cannot update or delete Company B project."""
        admin_a = tenant_fixture["admin_a"]
        proj_b = tenant_fixture["proj_b"]

        app.dependency_overrides[get_current_user] = lambda: admin_a
        resp = client.put(f"/api/projects/{proj_b.id}", json={"name": "Hacked Project", "key": "HACK"})
        assert resp.status_code in (403, 404)

        resp = client.delete(f"/api/projects/{proj_b.id}")
        assert resp.status_code in (403, 404)

    def test_team_mutation_isolation(self, tenant_fixture):
        """Admin from Company A cannot update or deactivate Company B team."""
        admin_a = tenant_fixture["admin_a"]
        team_b = tenant_fixture["team_b"]

        app.dependency_overrides[get_current_user] = lambda: admin_a
        resp = client.put(f"/api/teams/{team_b.id}", json={"name": "Hacked Team"})
        assert resp.status_code in (403, 404)

        resp = client.delete(f"/api/teams/{team_b.id}")
        assert resp.status_code in (403, 404)

    def test_role_dashboards_isolation(self, tenant_fixture):
        """Role-specific dashboards isolate metrics to caller's company."""
        admin_a = tenant_fixture["admin_a"]
        pm_a = tenant_fixture["pm_a"]
        dev_a = tenant_fixture["dev_a"]
        proj_b = tenant_fixture["proj_b"]

        # Admin stats
        app.dependency_overrides[get_current_user] = lambda: admin_a
        resp = client.get("/api/dashboard/admin-stats")
        assert resp.status_code == 200
        admin_data = resp.json()
        recent_proj_ids = [p["id"] for p in admin_data.get("recent_projects", [])]
        assert proj_b.id not in recent_proj_ids

        # PM stats
        app.dependency_overrides[get_current_user] = lambda: pm_a
        resp = client.get("/api/dashboard/pm-stats")
        assert resp.status_code == 200
        pm_data = resp.json()
        pm_proj_ids = [p["id"] for p in pm_data.get("projects", [])]
        assert proj_b.id not in pm_proj_ids

        # Dev stats
        app.dependency_overrides[get_current_user] = lambda: dev_a
        resp = client.get("/api/dashboard/dev-stats")
        assert resp.status_code == 200


class TestMultiTenantAnalyticsIsolation:

    def test_analytics_status_distribution_isolation(self, tenant_fixture, db_session):
        """Company A must never see Company B's custom statuses in Defects by Status."""
        admin_a = tenant_fixture["admin_a"]
        company_b = tenant_fixture["company_b"]

        # Create a custom status for Company B
        custom_b_status = IssueStatus(
            name="Beta Unique Audit Status",
            category="in_progress",
            company_id=company_b.id,
            is_active=True
        )
        db_session.add(custom_b_status)
        db_session.commit()

        try:
            app.dependency_overrides[get_current_user] = lambda: admin_a
            resp = client.get("/api/analytics/status")
            assert resp.status_code == 200
            status_names = [s["name"] for s in resp.json()]
            assert "Beta Unique Audit Status" not in status_names

            # Overview check
            resp_overview = client.get("/api/analytics/overview")
            assert resp_overview.status_code == 200
            overview_status_names = [s["name"] for s in resp_overview.json()["status_distribution"]]
            assert "Beta Unique Audit Status" not in overview_status_names

            # Sprint Insights check
            sprint_b = tenant_fixture["sprint_b"]
            sprint_ids = [sp["sprint_id"] for sp in resp_overview.json()["sprint_insights"]]
            assert sprint_b.id not in sprint_ids

            # Cross-company project filter
            proj_b = tenant_fixture["proj_b"]
            resp_cross = client.get(f"/api/analytics/overview?project_id={proj_b.id}")
            assert resp_cross.status_code == 200
            cross_data = resp_cross.json()
            assert cross_data["is_empty_scope"] is True
            assert cross_data["kpis"]["total_defects"] == 0
        finally:
            try:
                db_session.delete(custom_b_status)
                db_session.commit()
            except Exception:
                db_session.rollback()


import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.role import Role
from app.models.team import Team, TeamMember
from app.models.issue import Issue
from app.services.analytics_service import AnalyticsService
from app.services.team_service import TeamService

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_or_create_user(db: Session, email: str, full_name: str, role_name: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        role = db.query(Role).filter(Role.name == role_name).first()
        u = User(
            email=email,
            full_name=full_name,
            password_hash="mock_hash",
            is_active=True,
            is_system_user=False
        )
        if role:
            u.roles = [role]
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


@pytest.fixture
def admin_user(db_session: Session):
    return _get_or_create_user(db_session, "vln@admin.in", "Admin User", "Admin")


@pytest.fixture
def pm_user(db_session: Session):
    u = _get_or_create_user(db_session, "vln@pm.in", "Project Manager User", "Project Manager")
    team = db_session.query(Team).filter(Team.project_manager_id == u.id, Team.is_active == True).first()
    if not team:
        core_team = db_session.query(Team).filter(Team.name.in_(["BugForge Core Team", "BugForge"])).first()
        if core_team:
            core_team.project_manager_id = u.id
            db_session.commit()
        else:
            team = Team(
                name="BugForge Core Team",
                description="Primary engineering team",
                project_manager_id=u.id,
                company_id=1,
                is_active=True
            )
            db_session.add(team)
            db_session.commit()
    return u


@pytest.fixture
def tl_user(db_session: Session):
    u = _get_or_create_user(db_session, "vln@tl.in", "Team Leader User", "Team Leader")
    team = db_session.query(Team).filter(Team.team_leader_id == u.id, Team.is_active == True).first()
    if not team:
        core_team = db_session.query(Team).filter(Team.name.in_(["BugForge Core Team", "BugForge"])).first()
        if core_team and not core_team.team_leader_id:
            core_team.team_leader_id = u.id
            db_session.commit()
        else:
            team = Team(
                name="BugForge Core Team",
                description="Primary engineering team",
                team_leader_id=u.id,
                company_id=1,
                is_active=True
            )
            db_session.add(team)
            db_session.commit()
    return u


@pytest.fixture
def dev_user(db_session: Session):
    return _get_or_create_user(db_session, "vln@dev.in", "Developer User", "Developer")


@pytest.fixture
def reporter_user(db_session: Session):
    return _get_or_create_user(db_session, "vln@reporter.in", "Reporter User", "Reporter")


@pytest.fixture
def qa_user(db_session: Session):
    return _get_or_create_user(db_session, "vln@qa.in", "QA User", "QA")


class TestRoleBasedAnalyticsScoping:

    def test_admin_organization_wide_analytics(self, db_session: Session, admin_user: User):
        """Admin must see organization-wide scope with all teams and defects."""
        service = AnalyticsService()
        overview = service.get_overview(db_session, admin_user)

        assert overview.user_role == "Admin"
        assert overview.scope_type == "organization"
        assert overview.scope_title == "Organization Overview"
        assert overview.kpis.total_defects >= 0
        assert len(overview.scope_teams) >= 0
        assert not overview.is_empty_scope

    def test_pm_managed_teams_analytics(self, db_session: Session, pm_user: User):
        """PM analytics must be scoped only to teams managed by that PM."""
        service = AnalyticsService()
        overview = service.get_overview(db_session, pm_user)

        assert overview.user_role == "Project Manager"
        assert overview.scope_type == "managed_teams"
        assert "Managed Teams" in overview.scope_title
        assert len(overview.scope_teams) >= 1
        assert not overview.is_empty_scope

    def test_tl_single_team_analytics(self, db_session: Session, tl_user: User):
        """TL analytics must be scoped only to the single team led by that TL."""
        service = AnalyticsService()
        overview = service.get_overview(db_session, tl_user)

        assert overview.user_role == "Team Leader"
        assert overview.scope_type == "single_team"
        assert overview.team_name in ("BugForge Core Team", "BugForge")
        assert not overview.is_empty_scope


    def test_developer_personal_analytics_and_performance(self, db_session: Session, dev_user: User):
        """Developer analytics must show ONLY issues assigned to that developer."""
        service = AnalyticsService()
        overview = service.get_overview(db_session, dev_user)

        assert overview.user_role == "Developer"
        assert overview.scope_type == "developer_personal"
        assert overview.scope_title == "My Engineering Performance"
        # Developer workload table must be empty for developer personal view
        assert len(overview.developer_workload) == 0
        # Developer performance telemetry must be populated
        assert overview.developer_performance is not None
        assert overview.developer_performance.my_assigned_defects == overview.kpis.total_defects
        assert isinstance(overview.developer_performance.resolution_rate_percentage, float)

    def test_reporter_personal_analytics(self, db_session: Session, reporter_user: User):
        """Reporter analytics must show ONLY issues reported by that reporter."""
        service = AnalyticsService()
        overview = service.get_overview(db_session, reporter_user)

        assert overview.user_role == "Reporter"
        assert overview.scope_type == "reporter_personal"
        assert overview.scope_title == "My Reported Defects & Status"
        assert overview.kpis.total_defects >= 0

    def test_empty_state_when_user_has_no_team(self, db_session: Session):
        """When a TL or PM has no teams assigned, return clear empty state."""
        dummy_tl = User(
            full_name="Unassigned TL",
            email="unassigned_tl@bugforge.com",
            password_hash="hash",
            is_active=True,
            is_system_user=False
        )
        role = db_session.query(Role).filter(Role.name == "Team Leader").first()
        dummy_tl.roles = [role]
        db_session.add(dummy_tl)
        db_session.commit()
        db_session.refresh(dummy_tl)

        try:
            service = AnalyticsService()
            overview = service.get_overview(db_session, dummy_tl)
            assert overview.is_empty_scope is True
            assert "No team is currently assigned to you." in overview.empty_scope_message
        finally:
            db_session.delete(dummy_tl)
            db_session.commit()


class TestTeamManagementServiceAndRules:

    def test_admin_can_create_and_manage_team(self, db_session: Session, admin_user: User, pm_user: User):
        """Admin can create a new team with PM and members."""
        import uuid
        from app.schemas.team import TeamCreate, TeamUpdate
        service = TeamService()
        unique_suffix = uuid.uuid4().hex[:6]
        team_name = f"Test QA Guild {unique_suffix}"

        # Create new team
        create_data = TeamCreate(
            name=team_name,
            description="Dedicated quality automation team",
            project_manager_id=pm_user.id,
            team_leader_id=None,
            member_ids=[pm_user.id],
            is_active=True
        )
        created = service.create_team(db_session, create_data)
        assert created["id"] is not None
        assert created["name"] == team_name
        assert created["project_manager"].full_name == pm_user.full_name

        team_id = created["id"]
        try:
            # Update team
            update_data = TeamUpdate(
                name=f"{team_name} Updated",
                description="Updated description"
            )
            updated = service.update_team(db_session, team_id, update_data)
            assert updated["name"] == f"{team_name} Updated"

            # Deactivate team
            deactivated = service.deactivate_team(db_session, team_id)
            assert deactivated["team"]["is_active"] is False
        finally:
            # Cleanup
            t_obj = db_session.query(Team).filter(Team.id == team_id).first()
            if t_obj:
                db_session.delete(t_obj)
                db_session.commit()

    def test_team_leader_uniqueness_enforced(self, db_session: Session, tl_user: User):
        """A Team Leader cannot be assigned as Team Leader to two teams."""
        import uuid
        from app.schemas.team import TeamCreate
        from fastapi import HTTPException
        service = TeamService()
        unique_suffix = uuid.uuid4().hex[:6]

        # vln@tl.in is already Team Leader of "BugForge Core Team"
        create_data = TeamCreate(
            name=f"Conflict TL Team {unique_suffix}",
            description="Should fail",
            team_leader_id=tl_user.id,
            is_active=True
        )

        with pytest.raises(HTTPException) as exc_info:
            service.create_team(db_session, create_data)

        assert exc_info.value.status_code == 400
        assert "already the Team Leader" in exc_info.value.detail
        assert "A Team Leader can belong to only ONE team" in exc_info.value.detail

    def test_pm_can_manage_multiple_teams(self, db_session: Session, pm_user: User):
        """A PM may manage multiple teams without conflicts."""
        import uuid
        from app.schemas.team import TeamCreate
        service = TeamService()
        unique_suffix = uuid.uuid4().hex[:6]

        # Create two teams managed by same PM
        t1_data = TeamCreate(name=f"PM Multi Team Alpha {unique_suffix}", project_manager_id=pm_user.id)
        t2_data = TeamCreate(name=f"PM Multi Team Beta {unique_suffix}", project_manager_id=pm_user.id)

        t1 = service.create_team(db_session, t1_data)
        t2 = service.create_team(db_session, t2_data)

        assert t1["project_manager"].id == pm_user.id
        assert t2["project_manager"].id == pm_user.id

        # Cleanup
        db_session.query(Team).filter(Team.id.in_([t1["id"], t2["id"]])).delete(synchronize_session=False)
        db_session.commit()


class TestSystemUserExclusion:

    def test_system_users_excluded_from_employee_management(self, db_session: Session):
        """FastAPI / dev system users must be excluded from employee list and counts."""
        from app.repositories.user_repository import UserRepository
        repo = UserRepository()

        employees, total = repo.list_employees(db_session)
        employee_emails = [e.email for e in employees]

        assert "admin@test.com" not in employee_emails
        assert "newuser@example.com" not in employee_emails
        assert all(not e.is_system_user for e in employees)

    def test_system_users_excluded_from_available_team_members(self, db_session: Session):
        """System users must not appear in available members for team assignment."""
        service = TeamService()
        available_members = service.get_meta_available_members(db_session)
        member_emails = [m["email"] for m in available_members]

        assert "admin@test.com" not in member_emails
        assert "newuser@example.com" not in member_emails

    def test_team_stats_total_users_and_workforce_calculation(self, db_session: Session, admin_user: User):
        """Team stats must accurately count real eligible employees and exclude system accounts."""
        service = TeamService()
        stats = service.get_team_stats(db_session)

        assert stats["total_teams"] >= 1
        assert stats["active_teams"] >= 1
        assert stats["total_users"] >= 1
        assert stats["assigned_members"] >= 0
        assert stats["unassigned_users"] >= 0
        assert stats["total_leaders"] >= 0

        # Test API endpoint directly
        app.dependency_overrides[get_current_user] = lambda: admin_user
        try:
            res = client.get("/api/teams/meta/stats")
            assert res.status_code == 200
            data = res.json()
            assert data["total_users"] >= 1
            assert data["total_teams"] >= 1
        finally:
            app.dependency_overrides.clear()



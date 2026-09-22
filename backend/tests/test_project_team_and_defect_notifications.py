"""
Tests for Project Team Assignment, PM/TL Project Access, and Defect Creation Notifications.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.core.database import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.role import Role
from app.models.team import Team
from app.models.project import Project
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity
from app.models.notification import Notification
from app.services.issue_service import IssueService
from app.schemas.issue import IssueCreate
from app.schemas.project import ProjectCreate


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def project_team_setup(db_session: Session):
    """
    Setup test data:
    - Company
    - PM User & Role
    - TL User & Role
    - QA User & Role
    - Reporter User & Role
    - Engineering Team (assigned PM & TL)
    - Default Issue Statuses
    """
    # 1. Company
    comp = db_session.query(Company).filter(Company.name == "TestProjectTeamCo").first()
    if not comp:
        comp = Company(name="TestProjectTeamCo", legal_name="Test Project Team Co Inc.", is_active=True)
        db_session.add(comp)
        db_session.flush()

    # Roles
    roles = {}
    for rname in ["Admin", "Project Manager", "Team Leader", "QA", "Reporter", "Developer"]:
        r = db_session.query(Role).filter(Role.name == rname).first()
        if not r:
            r = Role(name=rname, description=f"{rname} role")
            db_session.add(r)
            db_session.flush()
        roles[rname] = r

    # Users
    def make_user(email, name, role_name):
        u = db_session.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                full_name=name,
                password_hash="fakehashpw123",
                company_id=comp.id,
                is_active=True
            )
            u.roles.append(roles[role_name])
            db_session.add(u)
            db_session.flush()
        return u

    admin_user = make_user("admin_pt@test.com", "Admin PT", "Admin")
    pm_user = make_user("pm_pt@test.com", "PM Person", "Project Manager")
    tl_user = make_user("tl_pt@test.com", "TL Person", "Team Leader")
    qa_user = make_user("qa_pt@test.com", "QA Person", "QA")
    reporter_user = make_user("reporter_pt@test.com", "Reporter Person", "Reporter")

    # Team
    team = db_session.query(Team).filter(Team.name == "Alpha Squad PT").first()
    if not team:
        team = Team(
            name="Alpha Squad PT",
            description="Alpha test team",
            company_id=comp.id,
            project_manager_id=pm_user.id,
            team_leader_id=tl_user.id,
            is_active=True
        )
        db_session.add(team)
        db_session.flush()
    else:
        team.project_manager_id = pm_user.id
        team.team_leader_id = tl_user.id
        db_session.flush()

    # Statuses
    st_open = db_session.query(IssueStatus).filter(IssueStatus.company_id == comp.id, IssueStatus.name == "Open").first()
    if not st_open:
        st_open = IssueStatus(name="Open", category="open", company_id=comp.id, order_index=1, is_initial=True, is_active=True)
        db_session.add(st_open)
        db_session.flush()

    # Priority
    pri = db_session.query(IssuePriority).filter(IssuePriority.is_active == True).first()
    if not pri:
        pri = IssuePriority(name="Medium", is_active=True)
        db_session.add(pri)
        db_session.flush()

    # Severity
    sev = db_session.query(IssueSeverity).filter(IssueSeverity.is_active == True).first()
    if not sev:
        sev = IssueSeverity(name="Medium", is_active=True)
        db_session.add(sev)
        db_session.flush()

    db_session.commit()

    return {
        "company": comp,
        "admin": admin_user,
        "pm": pm_user,
        "tl": tl_user,
        "qa": qa_user,
        "reporter": reporter_user,
        "team": team,
        "status_open": st_open,
        "priority": pri,
        "severity": sev,
    }


def test_create_project_with_team_id(project_team_setup, db_session):
    """Creating a project with team_id sets team_id and syncs PM and TL."""
    data = project_team_setup
    client = TestClient(app)

    app.dependency_overrides[get_current_user] = lambda: data["admin"]

    k = f"T{uuid.uuid4().hex[:3].upper()}"
    resp = client.post("/api/projects", json={
        "name": f"Team Managed Project {k}",
        "key": k,
        "description": "Project assigned to team",
        "team_id": data["team"].id,
    })
    assert resp.status_code == 201
    proj = resp.json()
    assert proj["team_id"] == data["team"].id
    assert proj["team_name"] == "Alpha Squad PT"
    assert proj["project_manager_id"] == data["pm"].id
    assert proj["project_manager_name"] == data["pm"].full_name
    assert proj["team_leader_id"] == data["tl"].id
    assert proj["team_leader_name"] == data["tl"].full_name


def test_pm_and_tl_access_all_projects(project_team_setup, db_session):
    """PM and TL can list and view all projects within company, just like QA and Reporter."""
    data = project_team_setup
    client = TestClient(app)

    # 1. Admin creates another unassigned project
    app.dependency_overrides[get_current_user] = lambda: data["admin"]
    gk = f"G{uuid.uuid4().hex[:3].upper()}"
    resp = client.post("/api/projects", json={
        "name": f"General Project {gk}",
        "key": gk,
        "description": "Project without explicit PM or TL",
    })
    assert resp.status_code == 201
    unassigned_id = resp.json()["id"]

    # 2. PM should see all company projects in list_projects
    app.dependency_overrides[get_current_user] = lambda: data["pm"]
    resp_pm = client.get("/api/projects")
    assert resp_pm.status_code == 200
    pm_proj_ids = [p["id"] for p in resp_pm.json()]
    assert unassigned_id in pm_proj_ids

    # 3. PM should be able to get_project on unassigned project (previously 403)
    resp_pm_get = client.get(f"/api/projects/{unassigned_id}")
    assert resp_pm_get.status_code == 200
    assert resp_pm_get.json()["id"] == unassigned_id

    # 4. TL should see all company projects in list_projects
    app.dependency_overrides[get_current_user] = lambda: data["tl"]
    resp_tl = client.get("/api/projects")
    assert resp_tl.status_code == 200
    tl_proj_ids = [p["id"] for p in resp_tl.json()]
    assert unassigned_id in tl_proj_ids

    # 5. TL should be able to get_project on unassigned project (previously 403)
    resp_tl_get = client.get(f"/api/projects/{unassigned_id}")
    assert resp_tl_get.status_code == 200
    assert resp_tl_get.json()["id"] == unassigned_id

    # 6. PM and TL can view history of company projects
    resp_hist_pm = client.get(f"/api/projects/{unassigned_id}/history")
    assert resp_hist_pm.status_code == 200
    resp_hist_tl = client.get(f"/api/projects/{unassigned_id}/history")
    assert resp_hist_tl.status_code == 200


def test_defect_creation_notifies_pm_and_tl(project_team_setup, db_session):
    """When a defect is created, notifications are sent to PM and TL of the project."""
    data = project_team_setup
    client = TestClient(app)

    # First, get the project assigned to the team
    proj = db_session.query(Project).filter(Project.key == "TMP1").first()
    assert proj is not None

    # Clear prior notifications for PM and TL to check freshly created ones
    db_session.query(Notification).filter(
        Notification.recipient_id.in_([data["pm"].id, data["tl"].id]),
        Notification.notification_type == "DEFECT_CREATED"
    ).delete(synchronize_session=False)
    db_session.commit()

    # Reporter reports a defect
    app.dependency_overrides[get_current_user] = lambda: data["reporter"]

    resp = client.post("/api/issues", json={
        "title": "Critical Login Crash Bug",
        "description": "System crashes when clicking login button",
        "issue_type": "Defect",
        "project_id": proj.id,
        "priority_id": data["priority"].id,
        "severity_id": data["severity"].id,
        "status_id": data["status_open"].id,
    })
    assert resp.status_code == 201
    created_issue = resp.json()["issue"]

    # Verify notifications were created for both PM and TL
    pm_notif = db_session.query(Notification).filter(
        Notification.recipient_id == data["pm"].id,
        Notification.notification_type == "DEFECT_CREATED",
        Notification.entity_id == created_issue["id"]
    ).first()
    assert pm_notif is not None
    assert "Assign Developer & QA" in pm_notif.title
    assert "Critical Login Crash Bug" in pm_notif.message

    tl_notif = db_session.query(Notification).filter(
        Notification.recipient_id == data["tl"].id,
        Notification.notification_type == "DEFECT_CREATED",
        Notification.entity_id == created_issue["id"]
    ).first()
    assert tl_notif is not None
    assert "Assign Developer & QA" in tl_notif.title
    assert "Critical Login Crash Bug" in tl_notif.message


def test_non_defect_does_not_trigger_defect_notification(project_team_setup, db_session):
    """A Task or non-defect issue does not dispatch DEFECT_CREATED notifications."""
    data = project_team_setup
    client = TestClient(app)

    proj = db_session.query(Project).filter(Project.key == "TMP1").first()
    assert proj is not None

    app.dependency_overrides[get_current_user] = lambda: data["reporter"]

    resp = client.post("/api/issues", json={
        "title": "Database Optimization Task",
        "description": "Optimize indexes for performance",
        "issue_type": "Task",
        "project_id": proj.id,
        "priority_id": data["priority"].id,
        "severity_id": data["severity"].id,
        "status_id": data["status_open"].id,
    })
    assert resp.status_code == 201
    task_issue = resp.json()["issue"]

    # Verify no DEFECT_CREATED notifications were sent
    defect_notifs = db_session.query(Notification).filter(
        Notification.entity_id == task_issue["id"],
        Notification.notification_type == "DEFECT_CREATED"
    ).all()
    assert len(defect_notifs) == 0

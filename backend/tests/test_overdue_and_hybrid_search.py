"""
Automated Test Suite for:
1. 24-Hour Unassigned Issue Calculation (Strict > 24h boundary, team assignment vs dev assignment)
2. Canonical BugForge Client Feature Binding & Serialization
3. Unified Hybrid Search (Empty query, keyword ranking, tenant isolation, graceful fallback)
"""
import uuid
from datetime import datetime, timedelta, timezone
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
from app.services.issue_service import IssueService


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def setup_data(db_session: Session):
    # 1. BugForge Company (internal)
    bf_company = db_session.query(Company).filter(Company.name == "BugForge").first()
    if not bf_company:
        bf_company = Company(id=1, name="BugForge", is_active=True)
        db_session.add(bf_company)
        db_session.flush()

    # 2. Customer Companies
    c1 = db_session.query(Company).filter(Company.name == "Test Corp Alpha").first()
    if not c1:
        c1 = Company(name="Test Corp Alpha", is_active=True)
        db_session.add(c1)
        db_session.flush()

    c2 = db_session.query(Company).filter(Company.name == "Test Corp Beta").first()
    if not c2:
        c2 = Company(name="Test Corp Beta", is_active=True)
        db_session.add(c2)
        db_session.flush()

    # Roles
    r_super_admin = db_session.query(Role).filter(Role.name == "Super Admin").first()
    if not r_super_admin:
        r_super_admin = Role(name="Super Admin")
        db_session.add(r_super_admin)
        db_session.flush()

    r_dev = db_session.query(Role).filter(Role.name == "Developer").first()
    if not r_dev:
        r_dev = Role(name="Developer")
        db_session.add(r_dev)
        db_session.flush()

    r_customer = db_session.query(Role).filter(Role.name == "Customer").first()
    if not r_customer:
        r_customer = Role(name="Customer")
        db_session.add(r_customer)
        db_session.flush()

    # Statuses
    open_status = db_session.query(IssueStatus).filter(IssueStatus.name == "Open", IssueStatus.company_id == bf_company.id).first()
    if not open_status:
        open_status = IssueStatus(company_id=bf_company.id, name="Open", category="open", is_initial=True)
        db_session.add(open_status)
        db_session.flush()

    # Priorities & Severities
    med_priority = db_session.query(IssuePriority).filter(IssuePriority.name == "Medium").first()
    if not med_priority:
        med_priority = IssuePriority(name="Medium")
        db_session.add(med_priority)
        db_session.flush()

    med_severity = db_session.query(IssueSeverity).filter(IssueSeverity.name == "Medium").first()
    if not med_severity:
        med_severity = IssueSeverity(name="Medium")
        db_session.add(med_severity)
        db_session.flush()

    # Users
    super_admin_user = db_session.query(User).filter(User.email == "sa_test@bugforge.internal").first()
    if not super_admin_user:
        super_admin_user = User(
            email="sa_test@bugforge.internal",
            full_name="Super Admin User",
            password_hash="fakehash",
            company_id=bf_company.id,
            is_active=True
        )
        super_admin_user.roles = [r_super_admin]
        db_session.add(super_admin_user)
        db_session.flush()
    else:
        super_admin_user.company_id = bf_company.id
        super_admin_user.is_active = True
        super_admin_user.roles = [r_super_admin]
        db_session.flush()

    dev_user = db_session.query(User).filter(User.email == "dev_test@bugforge.internal").first()
    if not dev_user:
        dev_user = User(
            email="dev_test@bugforge.internal",
            full_name="Test Developer",
            password_hash="fakehash",
            company_id=bf_company.id,
            is_active=True
        )
        dev_user.roles = [r_dev]
        db_session.add(dev_user)
        db_session.flush()
    else:
        dev_user.company_id = bf_company.id
        dev_user.is_active = True
        dev_user.roles = [r_dev]
        db_session.flush()

    customer_user_c1 = db_session.query(User).filter(User.email == "client_a@testalpha.com").first()
    if not customer_user_c1:
        customer_user_c1 = User(
            email="client_a@testalpha.com",
            full_name="Client Alpha User",
            password_hash="fakehash",
            company_id=c1.id,
            is_active=True
        )
        customer_user_c1.roles = [r_customer]
        db_session.add(customer_user_c1)
        db_session.flush()
    else:
        customer_user_c1.company_id = c1.id
        customer_user_c1.is_active = True
        customer_user_c1.roles = [r_customer]
        db_session.flush()

    customer_user_c2 = db_session.query(User).filter(User.email == "client_b@testbeta.com").first()
    if not customer_user_c2:
        customer_user_c2 = User(
            email="client_b@testbeta.com",
            full_name="Client Beta User",
            password_hash="fakehash",
            company_id=c2.id,
            is_active=True
        )
        customer_user_c2.roles = [r_customer]
        db_session.add(customer_user_c2)
        db_session.flush()
    else:
        customer_user_c2.company_id = c2.id
        customer_user_c2.is_active = True
        customer_user_c2.roles = [r_customer]
        db_session.flush()

    # Team
    team = db_session.query(Team).filter(Team.name == "Alpha Squad").first()
    if not team:
        team = Team(name="Alpha Squad", company_id=bf_company.id)
        db_session.add(team)
        db_session.flush()

    # Canonical BugForge project
    bf_project = db_session.query(Project).filter(Project.company_id == bf_company.id, Project.name == "BugForge").first()
    if not bf_project:
        bf_project = Project(name="BugForge", key="BF", company_id=bf_company.id, status="Active", created_by=super_admin_user.id)
        db_session.add(bf_project)
        db_session.flush()

    # Customer C1 project
    c1_project = db_session.query(Project).filter(Project.company_id == c1.id, Project.key == "C1P").first()
    if not c1_project:
        c1_project = Project(name="Alpha App", key="C1P", company_id=c1.id, status="Active", created_by=super_admin_user.id)
        db_session.add(c1_project)
        db_session.flush()

    # Customer C2 project
    c2_project = db_session.query(Project).filter(Project.company_id == c2.id, Project.key == "C2P").first()
    if not c2_project:
        c2_project = Project(name="Beta Portal", key="C2P", company_id=c2.id, status="Active", created_by=super_admin_user.id)
        db_session.add(c2_project)
        db_session.flush()

    db_session.commit()

    return {
        "bf_company": bf_company,
        "c1": c1,
        "c2": c2,
        "super_admin": super_admin_user,
        "dev_user": dev_user,
        "customer_c1": customer_user_c1,
        "customer_c2": customer_user_c2,
        "team": team,
        "bf_project": bf_project,
        "c1_project": c1_project,
        "c2_project": c2_project,
        "open_status": open_status,
        "priority": med_priority,
        "severity": med_severity,
    }


# ==============================================================================
# TEST 1: 24-HOUR UNASSIGNED LOGIC & BOUNDARY CONDITIONS
# ==============================================================================
def test_24h_unassigned_boundary_conditions(db_session: Session, setup_data):
    """
    Test strict > 24 hours boundary:
    - Exactly 23 hours 59 minutes: is_unassigned_over_24h == False
    - Exactly 24 hours 1 minute: is_unassigned_over_24h == True
    - Assigned to dev: is_unassigned_over_24h == False
    - Team assigned but dev unassigned (> 24h): is_unassigned_over_24h == True
    """
    c1 = setup_data["c1"]
    c1_project = setup_data["c1_project"]
    open_status = setup_data["open_status"]
    dev_user = setup_data["dev_user"]
    team = setup_data["team"]
    user = setup_data["customer_c1"]

    now = datetime.now(timezone.utc)
    u = uuid.uuid4().hex[:6].upper()

    # 1. Created 23 hours 59 minutes ago (boundary: strictly > 24 hours required)
    issue_recent = Issue(
        issue_key=f"C1P-{u}-01",
        title="Recent Unassigned Issue (23h 59m)",
        description="This issue was created just under 24 hours ago.",
        company_id=c1.id,
        project_id=c1_project.id,
        status_id=open_status.id,
        priority_id=setup_data["priority"].id,
        severity_id=setup_data["severity"].id,
        issue_type="Defect",
        assigned_to=None,
        team_id=None,
        created_at=now - timedelta(hours=23, minutes=59),
        reporter_id=user.id,
    )
    db_session.add(issue_recent)

    # 2. Created 24 hours 2 minutes ago (strictly > 24 hours)
    issue_overdue = Issue(
        issue_key=f"C1P-{u}-02",
        title="Overdue Unassigned Issue (24h 2m)",
        description="This issue was created strictly over 24 hours ago and is unassigned.",
        company_id=c1.id,
        project_id=c1_project.id,
        status_id=open_status.id,
        priority_id=setup_data["priority"].id,
        severity_id=setup_data["severity"].id,
        issue_type="Defect",
        assigned_to=None,
        team_id=None,
        created_at=now - timedelta(hours=24, minutes=2),
        reporter_id=user.id,
    )
    db_session.add(issue_overdue)

    # 3. Created 48 hours ago, with team assigned, but developer UNASSIGNED
    # Rule: Team assignment alone does NOT count as developer assignment.
    issue_team_only = Issue(
        issue_key=f"C1P-{u}-03",
        title="Overdue Issue with Team Only",
        description="This issue has squad assigned but no developer assigned.",
        company_id=c1.id,
        project_id=c1_project.id,
        status_id=open_status.id,
        priority_id=setup_data["priority"].id,
        severity_id=setup_data["severity"].id,
        issue_type="Defect",
        assigned_to=None,
        team_id=team.id,
        created_at=now - timedelta(hours=48),
        reporter_id=user.id,
    )
    db_session.add(issue_team_only)

    # 4. Created 48 hours ago, assigned to Developer
    # Rule: Assigned to developer removes the highlight immediately.
    issue_dev_assigned = Issue(
        issue_key=f"C1P-{u}-04",
        title="Overdue Issue with Dev Assigned",
        description="This issue is old but assigned to a developer.",
        company_id=c1.id,
        project_id=c1_project.id,
        status_id=open_status.id,
        priority_id=setup_data["priority"].id,
        severity_id=setup_data["severity"].id,
        issue_type="Defect",
        assigned_to=dev_user.id,
        team_id=team.id,
        created_at=now - timedelta(hours=48),
        reporter_id=user.id,
    )
    db_session.add(issue_dev_assigned)
    db_session.commit()

    # Query via API with user context
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    response = client.get(f"/api/issues/{issue_recent.id}")
    assert response.status_code == 200
    data_recent = response.json()
    assert data_recent["is_unassigned_over_24h"] is False
    assert data_recent["isUnassignedOver24Hours"] is False

    response = client.get(f"/api/issues/{issue_overdue.id}")
    assert response.status_code == 200
    data_overdue = response.json()
    assert data_overdue["is_unassigned_over_24h"] is True
    assert data_overdue["isUnassignedOver24Hours"] is True

    response = client.get(f"/api/issues/{issue_team_only.id}")
    assert response.status_code == 200
    data_team_only = response.json()
    assert data_team_only["is_unassigned_over_24h"] is True
    assert data_team_only["isUnassignedOver24Hours"] is True

    response = client.get(f"/api/issues/{issue_dev_assigned.id}")
    assert response.status_code == 200
    data_dev_assigned = response.json()
    assert data_dev_assigned["is_unassigned_over_24h"] is False
    assert data_dev_assigned["isUnassignedOver24Hours"] is False

    # Dynamic assignment check: assign dev to issue_overdue and re-check
    issue_overdue.assigned_to = dev_user.id
    db_session.commit()

    response = client.get(f"/api/issues/{issue_overdue.id}")
    assert response.status_code == 200
    assert response.json()["is_unassigned_over_24h"] is False

    app.dependency_overrides.clear()


# ==============================================================================
# TEST 2: CANONICAL BUGFORGE FEATURE REQUEST BINDING
# ==============================================================================
def test_client_feature_request_canonical_bugforge_binding(db_session: Session, setup_data):
    """
    Test customer client feature request:
    - Binds to canonical internal Project = "BugForge" (key: "BF")
    - Retains requesting customer company & user
    """
    c1 = setup_data["c1"]
    customer_user = setup_data["customer_c1"]
    open_status = setup_data["open_status"]

    app.dependency_overrides[get_current_user] = lambda: customer_user
    client = TestClient(app)

    # Post a Feature request
    payload = {
        "title": "Add Automated PDF Export for Monthly Invoices",
        "description": "Customer needs to export monthly PDF receipts directly from dashboard.",
        "issue_type": "Feature",
        "project_id": setup_data["c1_project"].id,
        "priority_id": setup_data["priority"].id,
        "severity_id": setup_data["severity"].id,
        "status_id": open_status.id,
    }

    res = client.post("/api/issues", json=payload)
    assert res.status_code in (200, 201)
    data = res.json()
    created = data.get("issue", data)

    # Check canonical project assignment
    assert created["project_name"] == "BugForge"
    assert created["issue_key"].startswith("BF")
    assert created["requesting_company_id"] == c1.id
    assert created["requesting_company_name"] == "Test Corp Alpha"
    assert created["reporter_id"] == customer_user.id

    app.dependency_overrides.clear()


# ==============================================================================
# TEST 3: UNIFIED HYBRID SEARCH & STRICT TENANT ISOLATION
# ==============================================================================
def test_hybrid_search_empty_keyword_and_tenant_isolation(db_session: Session, setup_data):
    """
    Test hybrid search:
    - Empty query: returns all issues matching filters for current tenant
    - Keyword query: matches by ID and title
    - Strict tenant isolation: customer C1 cannot see customer C2's issues
    """
    c1 = setup_data["c1"]
    c2 = setup_data["c2"]
    c1_project = setup_data["c1_project"]
    c2_project = setup_data["c2_project"]
    user_c1 = setup_data["customer_c1"]
    user_c2 = setup_data["customer_c2"]
    open_status = setup_data["open_status"]

    # Create distinct issues in C1 and C2
    u = uuid.uuid4().hex[:6].upper()
    unique_keyword = f"PayGateway{u}"
    issue_c1 = Issue(
        issue_key=f"C1P-{u}-05",
        title=f"Alpha Unique {unique_keyword} Failure",
        description="Stripe webhook signature validation failed on subscription renew.",
        company_id=c1.id,
        project_id=c1_project.id,
        status_id=open_status.id,
        priority_id=setup_data["priority"].id,
        severity_id=setup_data["severity"].id,
        issue_type="Defect",
        reporter_id=user_c1.id,
    )
    issue_c2 = Issue(
        issue_key=f"C2P-{u}-01",
        title="Beta Secret Confidential Vulnerability",
        description="Internal admin token exposed in response body.",
        company_id=c2.id,
        project_id=c2_project.id,
        status_id=open_status.id,
        priority_id=setup_data["priority"].id,
        severity_id=setup_data["severity"].id,
        issue_type="Defect",
        reporter_id=user_c2.id,
    )
    db_session.add(issue_c1)
    db_session.add(issue_c2)
    db_session.commit()

    # 1. As C1 user, search empty query via hybrid endpoint
    app.dependency_overrides[get_current_user] = lambda: user_c1
    client = TestClient(app)

    res = client.post("/api/issues/hybrid-search", json={"query": ""})
    assert res.status_code == 200
    results = res.json()
    c1_ids = [item["id"] for item in results]
    assert issue_c1.id in c1_ids
    # Crucial tenant security test: C2 issue MUST NOT be present
    assert issue_c2.id not in c1_ids

    # 2. As C1 user, search keyword unique_keyword
    res = client.post("/api/issues/hybrid-search", json={"query": unique_keyword})
    assert res.status_code == 200
    kw_results = res.json()
    assert len(kw_results) >= 1
    assert kw_results[0]["id"] == issue_c1.id

    # 3. As C1 user, attempt to search C2's confidential issue
    res = client.post("/api/issues/hybrid-search", json={"query": "Confidential Vulnerability"})
    assert res.status_code == 200
    leak_check = res.json()
    assert all(item["id"] != issue_c2.id for item in leak_check)

    # 4. As C1 user, search exact issue ID
    res = client.post("/api/issues/hybrid-search", json={"query": str(issue_c1.id)})
    assert res.status_code == 200
    id_results = res.json()
    assert len(id_results) >= 1
    assert id_results[0]["id"] == issue_c1.id

    app.dependency_overrides.clear()

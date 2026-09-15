"""
Automated Test Suite for:
1. 1-Hour QA Unassigned Calculation (Strict > 1h boundary after developer fix when status is Resolved)
2. Targeted QA Notification Routing (Dispatched strictly to assigned QA when assigned; broadcast to all QAs when unassigned)
3. Direct QA Assignment Endpoint (/api/issues/{issue_id}/assign-qa) and Audit Logging
4. Automatic Setting/Resetting of developer_fixed_at on Status Transitions
5. Multi-Tenant Masking of Assigned QA for External Client Views
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
from app.models.project import Project
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity
from app.models.notification import Notification
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
    # 1. BugForge Company
    bf_company = db_session.query(Company).filter(Company.name == "BugForge").first()
    if not bf_company:
        bf_company = Company(id=1, name="BugForge", is_active=True)
        db_session.add(bf_company)
        db_session.flush()

    # 2. Customer Company
    client_co = db_session.query(Company).filter(Company.name == "QA Test Corp").first()
    if not client_co:
        client_co = Company(name="QA Test Corp", is_active=True)
        db_session.add(client_co)
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

    r_qa = db_session.query(Role).filter(Role.name == "QA").first()
    if not r_qa:
        r_qa = Role(name="QA")
        db_session.add(r_qa)
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

    in_progress_status = db_session.query(IssueStatus).filter(IssueStatus.name == "In Progress", IssueStatus.company_id == bf_company.id).first()
    if not in_progress_status:
        in_progress_status = IssueStatus(company_id=bf_company.id, name="In Progress", category="in_progress")
        db_session.add(in_progress_status)
        db_session.flush()

    resolved_status = db_session.query(IssueStatus).filter(IssueStatus.name == "Resolved", IssueStatus.company_id == bf_company.id).first()
    if not resolved_status:
        resolved_status = IssueStatus(company_id=bf_company.id, name="Resolved", category="resolved")
        db_session.add(resolved_status)
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
    admin_user = db_session.query(User).filter(User.email == "admin_qa_test@bugforge.internal").first()
    if not admin_user:
        admin_user = User(
            email="admin_qa_test@bugforge.internal",
            full_name="QA Test Admin",
            password_hash="fakehash",
            company_id=bf_company.id,
            is_active=True
        )
        admin_user.roles = [r_super_admin]
        db_session.add(admin_user)
        db_session.flush()

    dev_user = db_session.query(User).filter(User.email == "dev_qa_test@bugforge.internal").first()
    if not dev_user:
        dev_user = User(
            email="dev_qa_test@bugforge.internal",
            full_name="QA Test Dev",
            password_hash="fakehash",
            company_id=bf_company.id,
            is_active=True
        )
        dev_user.roles = [r_dev]
        db_session.add(dev_user)
        db_session.flush()

    qa1_user = db_session.query(User).filter(User.email == "qa1_test@bugforge.internal").first()
    if not qa1_user:
        qa1_user = User(
            email="qa1_test@bugforge.internal",
            full_name="QA Engineer One",
            password_hash="fakehash",
            company_id=bf_company.id,
            is_active=True
        )
        qa1_user.roles = [r_qa]
        db_session.add(qa1_user)
        db_session.flush()

    qa2_user = db_session.query(User).filter(User.email == "qa2_test@bugforge.internal").first()
    if not qa2_user:
        qa2_user = User(
            email="qa2_test@bugforge.internal",
            full_name="QA Engineer Two",
            password_hash="fakehash",
            company_id=bf_company.id,
            is_active=True
        )
        qa2_user.roles = [r_qa]
        db_session.add(qa2_user)
        db_session.flush()

    other_co_qa = db_session.query(User).filter(User.email == "external_qa@clientco.com").first()
    if not other_co_qa:
        other_co_qa = User(
            email="external_qa@clientco.com",
            full_name="External QA",
            password_hash="fakehash",
            company_id=client_co.id,
            is_active=True
        )
        other_co_qa.roles = [r_qa]
        db_session.add(other_co_qa)
        db_session.flush()

    customer_user = db_session.query(User).filter(User.email == "client_user@clientco.com").first()
    if not customer_user:
        customer_user = User(
            email="client_user@clientco.com",
            full_name="Client Customer",
            password_hash="fakehash",
            company_id=client_co.id,
            is_active=True
        )
        customer_user.roles = [r_customer]
        db_session.add(customer_user)
        db_session.flush()

    # Project
    bf_project = db_session.query(Project).filter(Project.company_id == bf_company.id, Project.key == "QAP").first()
    if not bf_project:
        bf_project = Project(name="QA Test Project", key="QAP", company_id=bf_company.id, status="Active", created_by=admin_user.id)
        db_session.add(bf_project)
        db_session.flush()

    db_session.commit()

    return {
        "bf_company": bf_company,
        "client_co": client_co,
        "admin_user": admin_user,
        "dev_user": dev_user,
        "qa1_user": qa1_user,
        "qa2_user": qa2_user,
        "other_co_qa": other_co_qa,
        "customer_user": customer_user,
        "open_status": open_status,
        "in_progress_status": in_progress_status,
        "resolved_status": resolved_status,
        "med_priority": med_priority,
        "med_severity": med_severity,
        "bf_project": bf_project,
    }


def test_qa_unassigned_over_1_hour_boundary(db_session: Session, setup_data):
    """
    Test SLA Overdue for QA Assignment:
    - Status Resolved, QA None, developer_fixed_at 70 mins ago (> 1 hour) -> is_qa_unassigned_over_1h == True
    - Status Resolved, QA None, developer_fixed_at 40 mins ago (< 1 hour) -> is_qa_unassigned_over_1h == False
    - Status Resolved, QA Assigned, developer_fixed_at 90 mins ago -> is_qa_unassigned_over_1h == False
    - Status Open, QA None, developer_fixed_at 90 mins ago -> is_qa_unassigned_over_1h == False
    """
    now = datetime.now(timezone.utc)

    # 1. Overdue (>1 hour, no QA assigned)
    issue_overdue = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Overdue QA Issue",
        description="Detailed description for overdue QA issue",
        issue_type="defect",
        status_id=setup_data["resolved_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=None,
        developer_fixed_at=now - timedelta(minutes=70)
    )
    db_session.add(issue_overdue)

    # 2. Not Overdue (<1 hour, no QA assigned)
    issue_recent = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Recent Resolved Issue",
        description="Recent resolved test defect",
        issue_type="defect",
        status_id=setup_data["resolved_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=None,
        developer_fixed_at=now - timedelta(minutes=40)
    )
    db_session.add(issue_recent)

    # 3. Assigned QA (even if >1 hour, should NOT be overdue)
    issue_assigned = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Assigned QA Issue",
        description="Assigned QA test defect",
        issue_type="defect",
        status_id=setup_data["resolved_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=setup_data["qa1_user"].id,
        developer_fixed_at=now - timedelta(minutes=90)
    )
    db_session.add(issue_assigned)

    # 4. Open status (not resolved, should NOT be QA overdue)
    issue_open = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Open Issue",
        description="Open status test defect",
        issue_type="defect",
        status_id=setup_data["open_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=None,
        developer_fixed_at=None
    )
    db_session.add(issue_open)

    db_session.commit()

    # Query via API
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: setup_data["admin_user"]

    try:
        resp = client.get("/api/issues")
        assert resp.status_code == 200
        data = resp.json()
        issues_map = {item["id"]: item for item in data}

        assert issues_map[issue_overdue.id]["is_qa_unassigned_over_1h"] is True
        assert issues_map[issue_overdue.id]["isQaUnassignedOver1Hour"] is True

        assert issues_map[issue_recent.id]["is_qa_unassigned_over_1h"] is False
        assert issues_map[issue_recent.id]["isQaUnassignedOver1Hour"] is False

        assert issues_map[issue_assigned.id]["is_qa_unassigned_over_1h"] is False
        assert issues_map[issue_assigned.id]["isQaUnassignedOver1Hour"] is False
        assert issues_map[issue_assigned.id]["assigned_qa_name"] == setup_data["qa1_user"].full_name

        assert issues_map[issue_open.id]["is_qa_unassigned_over_1h"] is False
    finally:
        app.dependency_overrides.clear()


def test_targeted_qa_notification_routing(db_session: Session, setup_data):
    """
    Test that when an issue is resolved:
    - If assigned_qa_id is QA1, notification FEATURE_READY_FOR_QA is sent ONLY to QA1.
    - QA2 should not receive the notification.
    """
    issue = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Targeted QA Notification Test",
        description="Targeted notification QA test defect",
        issue_type="defect",
        status_id=setup_data["in_progress_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=setup_data["qa1_user"].id
    )
    db_session.add(issue)
    db_session.commit()

    service = IssueService()

    # Count existing notifications for QA1 and QA2
    count_qa1_before = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa1_user"].id).count()
    count_qa2_before = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa2_user"].id).count()

    # Dev resolves the issue
    service.notify_status_change(
        db=db_session,
        issue=issue,
        old_status_id=setup_data["in_progress_status"].id,
        new_status_id=setup_data["resolved_status"].id,
        actor=setup_data["dev_user"]
    )

    count_qa1_after = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa1_user"].id).count()
    count_qa2_after = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa2_user"].id).count()

    # QA1 should receive exactly 1 notification
    assert count_qa1_after == count_qa1_before + 1

    # QA2 must NOT receive any notification
    assert count_qa2_after == count_qa2_before

    # Verify notification details
    latest_notif = db_session.query(Notification).filter(
        Notification.recipient_id == setup_data["qa1_user"].id
    ).order_by(Notification.created_at.desc()).first()

    assert latest_notif.notification_type == "FEATURE_READY_FOR_QA"
    assert issue.issue_key in latest_notif.message


def test_broadcast_qa_notification_when_qa_unassigned(db_session: Session, setup_data):
    """
    When assigned_qa_id is None and issue is resolved:
    - Notification is broadcasted to all active QAs in the company (QA1 and QA2).
    """
    issue = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Broadcast QA Notification Test",
        description="Broadcast notification QA test defect",
        issue_type="defect",
        status_id=setup_data["in_progress_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=None
    )
    db_session.add(issue)
    db_session.commit()

    service = IssueService()

    count_qa1_before = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa1_user"].id).count()
    count_qa2_before = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa2_user"].id).count()

    service.notify_status_change(
        db=db_session,
        issue=issue,
        old_status_id=setup_data["in_progress_status"].id,
        new_status_id=setup_data["resolved_status"].id,
        actor=setup_data["dev_user"]
    )

    count_qa1_after = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa1_user"].id).count()
    count_qa2_after = db_session.query(Notification).filter(Notification.recipient_id == setup_data["qa2_user"].id).count()

    # Both QA1 and QA2 receive notifications since no specific QA is assigned
    assert count_qa1_after == count_qa1_before + 1
    assert count_qa2_after == count_qa2_before + 1


def test_patch_assign_qa_endpoint(db_session: Session, setup_data):
    """
    Test direct assignment of QA via PATCH /api/issues/{id}/assign-qa:
    1. Successfully assigns QA and dispatches QA_ASSIGNED notification.
    2. Enforces company boundary (cannot assign QA from another company).
    """
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: setup_data["admin_user"]

    issue = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="QA Endpoint Assign Test",
        description="Endpoint assign test defect",
        issue_type="defect",
        status_id=setup_data["resolved_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=None,
        developer_fixed_at=datetime.now(timezone.utc) - timedelta(minutes=45)
    )
    db_session.add(issue)
    db_session.commit()

    try:
        # Cross-company QA assignment should be rejected with 400
        cross_resp = client.patch(
            f"/api/issues/{issue.id}/assign-qa",
            json={"assigned_qa_id": setup_data["other_co_qa"].id}
        )
        assert cross_resp.status_code == 400

        # Valid QA assignment
        valid_resp = client.patch(
            f"/api/issues/{issue.id}/assign-qa",
            json={"assigned_qa_id": setup_data["qa2_user"].id}
        )
        assert valid_resp.status_code == 200
        data = valid_resp.json()
        assert data["assigned_qa_id"] == setup_data["qa2_user"].id
        assert data["assigned_qa_name"] == setup_data["qa2_user"].full_name

        # Verify QA_ASSIGNED notification was created for QA2
        qa2_notif = db_session.query(Notification).filter(
            Notification.recipient_id == setup_data["qa2_user"].id,
            Notification.notification_type == "QA_ASSIGNED"
        ).order_by(Notification.created_at.desc()).first()
        assert qa2_notif is not None
        assert issue.issue_key in qa2_notif.message
    finally:
        app.dependency_overrides.clear()


def test_developer_fixed_at_lifecycle_on_status_change(db_session: Session, setup_data):
    """
    Verify developer_fixed_at is set when moving to Resolved,
    and reset when reopening/moving back to In Progress.
    """
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: setup_data["dev_user"]

    issue = Issue(
        company_id=setup_data["bf_company"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Status Transition Fix Timestamp Test",
        description="Status transition fix timestamp test defect",
        issue_type="defect",
        status_id=setup_data["in_progress_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=None,
        developer_fixed_at=None
    )
    db_session.add(issue)
    db_session.commit()

    try:
        # 1. Dev marks as Resolved
        resp1 = client.patch(
            f"/api/issues/{issue.id}/status",
            json={"status_id": setup_data["resolved_status"].id}
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["developer_fixed_at"] is not None

        # 2. Issue rejected / moved back to In Progress
        resp2 = client.patch(
            f"/api/issues/{issue.id}/status",
            json={"status_id": setup_data["in_progress_status"].id}
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["developer_fixed_at"] is None
    finally:
        app.dependency_overrides.clear()


def test_customer_isolation_and_qa_masking(db_session: Session, setup_data):
    """
    External customer viewing BugForge internal tickets should have assigned_qa masked to 'BugForge QA Team'
    and assigned_qa_id masked to None.
    """
    client = TestClient(app)

    issue = Issue(
        company_id=setup_data["bf_company"].id,
        requesting_company_id=setup_data["client_co"].id,
        project_id=setup_data["bf_project"].id,
        issue_key=f"QAP-{uuid.uuid4().hex[:6].upper()}",
        title="Masking QA Test Issue",
        description="Masking QA test defect",
        issue_type="defect",
        status_id=setup_data["resolved_status"].id,
        priority_id=setup_data["med_priority"].id,
        severity_id=setup_data["med_severity"].id,
        reporter_id=setup_data["admin_user"].id,
        assigned_to=setup_data["dev_user"].id,
        assigned_qa_id=setup_data["qa1_user"].id,
        developer_fixed_at=datetime.now(timezone.utc)
    )
    db_session.add(issue)
    db_session.commit()

    try:
        # Customer user viewing
        app.dependency_overrides[get_current_user] = lambda: setup_data["customer_user"]
        resp = client.get(f"/api/issues/{issue.id}")
        assert resp.status_code == 200
        cust_data = resp.json()

        assert cust_data["assigned_qa_id"] is None
        assert cust_data["assigned_qa_name"] == "BugForge QA Team"

        # Super Admin viewing
        app.dependency_overrides[get_current_user] = lambda: setup_data["admin_user"]
        admin_resp = client.get(f"/api/issues/{issue.id}")
        assert admin_resp.status_code == 200
        admin_data = admin_resp.json()

        assert admin_data["assigned_qa_id"] == setup_data["qa1_user"].id
        assert admin_data["assigned_qa_name"] == setup_data["qa1_user"].full_name
    finally:
        app.dependency_overrides.clear()

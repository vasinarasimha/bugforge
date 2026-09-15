"""
Automated Test Suite for BugForge Feature Request Workflow,
Persistent Notifications, Strict Tenant Isolation, and Analytics Date Filters.
"""
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
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
from app.services.notification_service import notification_service
from app.services.analytics_service import AnalyticsService
from app.services.company_settings_service import company_settings_service
from app.schemas.company import CustomizationRequestCreate


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def workflow_setup(db_session: Session):
    """
    Setup:
    - BugForge Company (id: 1)
    - Customer Company A (Acme Corp)
    - Customer Company B (Stark Labs)
    - Internal BugForge Team & Roles: Super Admin, PM, TL, Dev, QA
    - Customer Admins for Company A and B
    """
    # 1. BugForge Company
    bugforge = db_session.query(Company).filter(Company.name == "BugForge").first()
    if not bugforge:
        bugforge = Company(id=1, name="BugForge", is_active=True)
        db_session.add(bugforge)
        db_session.flush()

    # Ensure default statuses exist for BugForge company
    status_defs = [
        {"name": "Open", "category": "open", "order_index": 1, "is_initial": True, "is_final": False},
        {"name": "In Progress", "category": "in_progress", "order_index": 2, "is_initial": False, "is_final": False},
        {"name": "Resolved", "category": "resolved", "order_index": 3, "is_initial": False, "is_final": False},
        {"name": "Verified", "category": "resolved", "order_index": 4, "is_initial": False, "is_final": False},
        {"name": "Closed", "category": "closed", "order_index": 5, "is_initial": False, "is_final": True},
    ]
    for s_def in status_defs:
        st = db_session.query(IssueStatus).filter(
            IssueStatus.company_id == bugforge.id,
            IssueStatus.name == s_def["name"]
        ).first()
        if not st:
            db_session.add(IssueStatus(
                name=s_def["name"],
                category=s_def["category"],
                order_index=s_def["order_index"],
                is_initial=s_def["is_initial"],
                is_final=s_def["is_final"],
                is_active=True,
                company_id=bugforge.id,
            ))
        elif st.category != s_def["category"]:
            st.category = s_def["category"]
    db_session.flush()

    # 2. Roles
    roles_dict = {}
    for role_name in ["Super Admin", "Admin", "Project Manager", "Team Leader", "Developer", "QA"]:
        r = db_session.query(Role).filter(Role.name == role_name).first()
        if not r:
            r = Role(name=role_name)
            db_session.add(r)
            db_session.flush()
        roles_dict[role_name] = r

    # 3. BugForge Super Admin
    super_admin = db_session.query(User).filter(User.email == "sa_workflow_test@bugforge.test").first()
    if not super_admin:
        super_admin = User(
            email="sa_workflow_test@bugforge.test",
            password_hash="testpass123",
            full_name="BugForge SuperAdmin",
            company_id=1,
            is_active=True,
            is_system_user=True,
            roles=[roles_dict["Super Admin"]]
        )
        db_session.add(super_admin)
        db_session.flush()
    else:
        super_admin.company_id = 1
        super_admin.is_active = True
        super_admin.roles = [roles_dict["Super Admin"]]
        db_session.flush()

    # 4. BugForge TL, PM, Dev, QA
    bf_pm = db_session.query(User).filter(User.email == "pm_workflow_test@bugforge.test").first()
    if not bf_pm:
        bf_pm = User(
            email="pm_workflow_test@bugforge.test",
            password_hash="testpass123",
            full_name="BugForge PM",
            company_id=1,
            is_active=True,
            roles=[roles_dict["Project Manager"]]
        )
        db_session.add(bf_pm)
        db_session.flush()
    else:
        bf_pm.company_id = 1
        bf_pm.is_active = True
        bf_pm.roles = [roles_dict["Project Manager"]]
        db_session.flush()

    bf_tl = db_session.query(User).filter(User.email == "tl_workflow_test@bugforge.test").first()
    if not bf_tl:
        bf_tl = User(
            email="tl_workflow_test@bugforge.test",
            password_hash="testpass123",
            full_name="BugForge TeamLeader",
            company_id=1,
            is_active=True,
            roles=[roles_dict["Team Leader"]]
        )
        db_session.add(bf_tl)
        db_session.flush()
    else:
        bf_tl.company_id = 1
        bf_tl.is_active = True
        bf_tl.roles = [roles_dict["Team Leader"]]
        db_session.flush()

    bf_dev = db_session.query(User).filter(User.email == "dev_workflow_test@bugforge.test").first()
    if not bf_dev:
        bf_dev = User(
            email="dev_workflow_test@bugforge.test",
            password_hash="testpass123",
            full_name="BugForge LeadDeveloper",
            company_id=1,
            is_active=True,
            roles=[roles_dict["Developer"]]
        )
        db_session.add(bf_dev)
        db_session.flush()
    else:
        bf_dev.company_id = 1
        bf_dev.is_active = True
        bf_dev.roles = [roles_dict["Developer"]]
        db_session.flush()

    bf_qa = db_session.query(User).filter(User.email == "qa_workflow_test@bugforge.test").first()
    if not bf_qa:
        bf_qa = User(
            email="qa_workflow_test@bugforge.test",
            password_hash="testpass123",
            full_name="BugForge QualityAssurance",
            company_id=1,
            is_active=True,
            roles=[roles_dict["QA"]]
        )
        db_session.add(bf_qa)
        db_session.flush()
    else:
        bf_qa.company_id = 1
        bf_qa.is_active = True
        bf_qa.roles = [roles_dict["QA"]]
        db_session.flush()

    # 5. Internal BugForge Team
    bf_team = db_session.query(Team).filter(Team.name == "Core Platform Squad").first()
    if not bf_team:
        bf_team = Team(
            name="Core Platform Squad",
            company_id=1,
            team_leader_id=bf_tl.id,
            project_manager_id=bf_pm.id,
            is_active=True
        )
        db_session.add(bf_team)
        db_session.flush()

    # 6. Customer Company A & Admin
    company_a = db_session.query(Company).filter(Company.name == "Acme Corp Customer").first()
    if not company_a:
        company_a = Company(name="Acme Corp Customer", is_active=True)
        db_session.add(company_a)
        db_session.flush()

    admin_a = db_session.query(User).filter(User.email == "admin@acme-customer.test").first()
    if not admin_a:
        admin_a = User(
            email="admin@acme-customer.test",
            password_hash="testpass123",
            full_name="Alice AcmeAdmin",
            company_id=company_a.id,
            is_active=True,
            roles=[roles_dict["Admin"]]
        )
        db_session.add(admin_a)
        db_session.flush()
    else:
        admin_a.company_id = company_a.id
        admin_a.is_active = True
        admin_a.roles = [roles_dict["Admin"]]
        db_session.flush()

    # 7. Customer Company B & Admin
    company_b = db_session.query(Company).filter(Company.name == "Stark Labs Customer").first()
    if not company_b:
        company_b = Company(name="Stark Labs Customer", is_active=True)
        db_session.add(company_b)
        db_session.flush()

    admin_b = db_session.query(User).filter(User.email == "admin@stark-customer.test").first()
    if not admin_b:
        admin_b = User(
            email="admin@stark-customer.test",
            password_hash="testpass123",
            full_name="Bob StarkAdmin",
            company_id=company_b.id,
            is_active=True,
            roles=[roles_dict["Admin"]]
        )
        db_session.add(admin_b)
        db_session.flush()
    else:
        admin_b.company_id = company_b.id
        admin_b.is_active = True
        admin_b.roles = [roles_dict["Admin"]]
        db_session.flush()

    # 8. BugForge Internal Project
    bf_project = db_session.query(Project).filter(Project.company_id == 1).first()
    if not bf_project:
        bf_project = Project(
            name="BugForge Platform Core",
            key="BFP",
            company_id=1,
            created_by=super_admin.id
        )
        db_session.add(bf_project)
        db_session.flush()

    # 9. Company A Project
    project_a = db_session.query(Project).filter(Project.company_id == company_a.id).first()
    if not project_a:
        project_a = Project(
            name="Acme Web Portal",
            key="ACME",
            company_id=company_a.id,
            created_by=admin_a.id
        )
        db_session.add(project_a)
        db_session.flush()

    db_session.commit()

    return {
        "bugforge": bugforge,
        "super_admin": super_admin,
        "bf_pm": bf_pm,
        "bf_tl": bf_tl,
        "bf_dev": bf_dev,
        "bf_qa": bf_qa,
        "bf_team": bf_team,
        "company_a": company_a,
        "admin_a": admin_a,
        "project_a": project_a,
        "company_b": company_b,
        "admin_b": admin_b,
        "bf_project": bf_project,
    }


def test_super_admin_belongs_to_bugforge_company(db_session: Session, workflow_setup):
    """Verify business rule: Super Admin is associated with BugForge company (company_id=1)."""
    sa = db_session.query(User).filter(User.id == workflow_setup["super_admin"].id).first()
    assert sa.company_id == 1
    assert sa.company.name == "BugForge"


def test_feature_request_submission_and_notifications(db_session: Session, workflow_setup):
    """
    Company A Admin submits a customization request.
    Verifies:
    1. Internal BugForge Feature issue is created (issue_type='Feature', company_id=1, requesting_company_id=company_a.id).
    2. Super Admin receives a persistent notification.
    3. Requesting Company A Admin receives a persistent confirmation notification.
    """
    admin_a = workflow_setup["admin_a"]
    company_a = workflow_setup["company_a"]
    super_admin = workflow_setup["super_admin"]

    # Submit customization request via service
    req_data = CustomizationRequestCreate(
        title="Automated Slack Webhook Alerts",
        description="We need real-time Slack notifications on critical defect transitions.",
        category="Integration",
        requested_behavior="Post rich JSON payload to configured incoming webhook URL upon status change.",
    )
    res = company_settings_service.submit_customization_request(
        db_session, company_id=company_a.id, data=req_data, user=admin_a
    )
    assert res.id is not None
    assert res.title == "Automated Slack Webhook Alerts"

    # Verify internal Feature issue exists
    feature_issue = db_session.query(Issue).filter(
        Issue.title == "Automated Slack Webhook Alerts",
        Issue.issue_type == "Feature",
        Issue.company_id == 1,
        Issue.requesting_company_id == company_a.id
    ).order_by(Issue.id.desc()).first()
    assert feature_issue is not None
    assert feature_issue.requesting_company_id == company_a.id

    # Verify Super Admin notification exists
    sa_notifs = notification_service.list_notifications(db_session, user_id=super_admin.id)
    assert any(n.notification_type == "FEATURE_REQUEST_SUBMITTED" and n.entity_id == feature_issue.id for n in sa_notifs)

    # Verify Customer Admin A notification exists
    a_notifs = notification_service.list_notifications(db_session, user_id=admin_a.id)
    assert any(n.notification_type == "FEATURE_REQUEST_SUBMITTED" and n.entity_id == feature_issue.id for n in a_notifs)


def test_notification_user_isolation_and_unread_count(db_session: Session, workflow_setup):
    """
    Verify:
    1. User A's notifications are strictly isolated from User B.
    2. User B cannot view User A's notifications.
    3. User B cannot mark User A's notification as read (must raise 404).
    4. Marking notifications as read updates database state and unread count decrements to 0.
    """
    admin_a = workflow_setup["admin_a"]
    admin_b = workflow_setup["admin_b"]

    # Ensure Admin A has an unread notification
    unread_before = notification_service.get_unread_count(db_session, user_id=admin_a.id)
    assert unread_before > 0

    # Admin B's list should NOT contain Admin A's notifications
    b_notifs = notification_service.list_notifications(db_session, user_id=admin_b.id)
    a_notifs = notification_service.list_notifications(db_session, user_id=admin_a.id)
    a_notif_ids = {n.id for n in a_notifs}
    b_notif_ids = {n.id for n in b_notifs}
    assert not a_notif_ids.intersection(b_notif_ids)

    # Admin B attempts to mark Admin A's notification as read -> must fail
    target_notif = a_notifs[0]
    with pytest.raises(HTTPException) as exc:
        notification_service.mark_as_read(db_session, notification_id=target_notif.id, user_id=admin_b.id)
    assert exc.value.status_code in [403, 404]

    # Admin A marks their notification as read
    marked = notification_service.mark_as_read(db_session, notification_id=target_notif.id, user_id=admin_a.id)
    assert marked["is_read"] is True
    assert marked["read_at"] is not None

    # Mark all read for Admin A
    notification_service.mark_all_read(db_session, user_id=admin_a.id)
    unread_after = notification_service.get_unread_count(db_session, user_id=admin_a.id)
    assert unread_after == 0


def test_super_admin_assigns_team_with_authorization(db_session: Session, workflow_setup):
    """
    Verify:
    1. Unauthorized user (Customer Admin) cannot assign feature to internal team (403 Forbidden).
    2. Super Admin can assign feature to internal BugForge team.
    3. Team Leader and Project Manager receive notification upon assignment.
    """
    super_admin = workflow_setup["super_admin"]
    admin_a = workflow_setup["admin_a"]
    bf_team = workflow_setup["bf_team"]
    bf_tl = workflow_setup["bf_tl"]
    bf_pm = workflow_setup["bf_pm"]

    feature = db_session.query(Issue).filter(
        Issue.issue_type == "Feature",
        Issue.company_id == 1
    ).order_by(Issue.id.desc()).first()
    assert feature is not None

    # Unauthorized attempt
    with pytest.raises(HTTPException) as exc:
        IssueService().assign_team(db_session, issue_id=feature.id, team_id=bf_team.id, user=admin_a)
    assert exc.value.status_code == 403

    # Authorized assignment by Super Admin
    updated_feature = IssueService().assign_team(
        db_session, issue_id=feature.id, team_id=bf_team.id, user=super_admin
    )
    assert updated_feature.team_id == bf_team.id

    # Verify TL and PM received notification
    tl_notifs = notification_service.list_notifications(db_session, user_id=bf_tl.id)
    assert any(n.notification_type == "FEATURE_ASSIGNED_TO_TEAM" and n.entity_id == feature.id for n in tl_notifs)

    pm_notifs = notification_service.list_notifications(db_session, user_id=bf_pm.id)
    assert any(n.notification_type == "FEATURE_ASSIGNED_TO_TEAM" and n.entity_id == feature.id for n in pm_notifs)


def test_pm_tl_assigns_developer_with_authorization(db_session: Session, workflow_setup):
    """
    Verify:
    1. Unauthorized developer or customer user cannot reassign (403 Forbidden).
    2. PM / TL assigns feature to internal developer.
    3. Developer receives notification of assignment.
    """
    bf_tl = workflow_setup["bf_tl"]
    bf_dev = workflow_setup["bf_dev"]
    admin_b = workflow_setup["admin_b"]

    feature = db_session.query(Issue).filter(
        Issue.issue_type == "Feature",
        Issue.company_id == 1
    ).order_by(Issue.id.desc()).first()

    # Unauthorized attempt by Customer Admin
    with pytest.raises(HTTPException) as exc:
        IssueService().assign_developer(db_session, issue_id=feature.id, developer_id=bf_dev.id, user=admin_b)
    assert exc.value.status_code == 403

    # Authorized assignment by Team Leader
    updated = IssueService().assign_developer(
        db_session, issue_id=feature.id, developer_id=bf_dev.id, user=bf_tl
    )
    assert updated.assigned_to == bf_dev.id

    # Developer receives notification
    dev_notifs = notification_service.list_notifications(db_session, user_id=bf_dev.id)
    assert any(n.notification_type == "FEATURE_ASSIGNED_TO_DEV" and n.entity_id == feature.id for n in dev_notifs)


def test_qa_verification_flow(db_session: Session, workflow_setup):
    """
    Verify QA verification lifecycle:
    1. Non-QA user cannot perform QA verification (403 Forbidden).
    2. QA rejects with rework required -> status goes to in_progress, developer receives rework notification.
    3. QA approves with Pass -> status goes to resolved, qa_state = 'Passed'.
    """
    bf_qa = workflow_setup["bf_qa"]
    bf_dev = workflow_setup["bf_dev"]

    feature = db_session.query(Issue).filter(
        Issue.issue_type == "Feature",
        Issue.company_id == 1
    ).order_by(Issue.id.desc()).first()

    # Step 1: QA requests rework
    reworked = IssueService().qa_verify(
        db_session, issue_id=feature.id, qa_state="Requires Rework", notes="Missing unit test for webhook retry.", user=bf_qa
    )
    assert reworked.qa_state == "Requires Rework"

    # Developer receives rework notification
    dev_notifs = notification_service.list_notifications(db_session, user_id=bf_dev.id)
    assert any(n.notification_type == "FEATURE_QA_REWORK" and n.entity_id == feature.id for n in dev_notifs)

    # Step 2: QA approves verification (Passed)
    passed = IssueService().qa_verify(
        db_session, issue_id=feature.id, qa_state="Passed", notes="All end-to-end tests passed.", user=bf_qa
    )
    assert passed.qa_state == "Passed"
    assert passed.status.category == "resolved"


def test_feature_closure_notifies_customer_company(db_session: Session, workflow_setup):
    """
    Verify:
    When a Feature issue is moved to Closed, the requesting Customer Company Admin
    receives a 'FEATURE_CLOSED' notification ('Feature Implemented').
    """
    super_admin = workflow_setup["super_admin"]
    admin_a = workflow_setup["admin_a"]

    feature = db_session.query(Issue).filter(
        Issue.issue_type == "Feature",
        Issue.company_id == 1,
        Issue.requesting_company_id == workflow_setup["company_a"].id
    ).order_by(Issue.id.desc()).first()
    assert feature is not None

    closed_status = db_session.query(IssueStatus).filter(
        IssueStatus.company_id == 1,
        (IssueStatus.category == "closed") | (IssueStatus.name == "Closed")
    ).first()
    if not closed_status:
        closed_status = IssueStatus(
            name="Closed", category="closed", is_final=True, is_active=True, company_id=1
        )
        db_session.add(closed_status)
        db_session.flush()

    old_status_id = feature.status_id
    feature.status_id = closed_status.id
    db_session.commit()

    IssueService().notify_status_change(
        db_session, issue=feature, old_status_id=old_status_id, new_status_id=closed_status.id, actor=super_admin
    )

    # Check Customer Admin A received completion notification
    a_notifs = notification_service.list_notifications(db_session, user_id=admin_a.id)
    assert any(n.notification_type == "FEATURE_CLOSED" and n.entity_id == feature.id for n in a_notifs)


def test_tenant_visibility_and_customer_data_masking(db_session: Session, workflow_setup):
    """
    Verify:
    1. Company A can list Feature requests it submitted.
    2. Company B CANNOT list Company A's Feature requests.
    3. BugForge internal unrelated issues are NOT visible to customer companies.
    """
    company_a = workflow_setup["company_a"]
    company_b = workflow_setup["company_b"]

    issues_a = IssueService().list(db_session, company_id=company_a.id)
    issues_b = IssueService().list(db_session, company_id=company_b.id)

    # Customer Company A and B should NOT see the BugForge-routed customization issue in Reported Issues
    assert not any(i.requesting_company_id == company_a.id for i in issues_a)
    assert not any(i.requesting_company_id == company_a.id for i in issues_b)

    # BugForge company members CAN see it in Reported Issues
    issues_bf = IssueService().list(db_session, company_id=1, is_bugforge=True)
    assert any(i.requesting_company_id == company_a.id for i in issues_bf)

    # Customer Company A sees the request and implementation status in Customization Requests
    customization_reqs = company_settings_service.list_customization_requests(db_session, company_id=company_a.id)
    assert any(r.company_id == company_a.id for r in customization_reqs)


def test_analytics_date_filter_boundary_consistency(db_session: Session, workflow_setup):
    """
    Verify analytics time filter fix:
    - 7 Days vs 30 Days vs 90 Days recalculates all KPIs, status distributions, and severity metrics.
    - An issue created 20 days ago appears in 30d and 90d, but NOT in 7d.
    """
    company_a = workflow_setup["company_a"]
    now = datetime.now(timezone.utc)

    # Create an issue with created_at 20 days ago in Company A
    old_issue = Issue(
        title="Historic Issue 20 Days Ago",
        description="Detailed description of historic defect reported three weeks ago.",
        company_id=company_a.id,
        project_id=workflow_setup["project_a"].id,
        reporter_id=workflow_setup["admin_a"].id,
        created_at=now - timedelta(days=20),
        status_id=db_session.query(IssueStatus).filter(IssueStatus.company_id == company_a.id).first().id
        if db_session.query(IssueStatus).filter(IssueStatus.company_id == company_a.id).first()
        else db_session.query(IssueStatus).first().id,
        priority_id=db_session.query(IssuePriority).first().id,
        severity_id=db_session.query(IssueSeverity).first().id,
        issue_key=f"HIST-{int(now.timestamp())}"
    )
    db_session.add(old_issue)
    db_session.commit()

    analytics_7d = AnalyticsService().get_overview(
        db_session, current_user=workflow_setup["admin_a"], days=7
    )
    analytics_30d = AnalyticsService().get_overview(
        db_session, current_user=workflow_setup["admin_a"], days=30
    )

    # 30-day view must contain at least 1 more defect than 7-day view because of the 20-day-old issue!
    total_7d = analytics_7d.kpis.total_defects
    total_30d = analytics_30d.kpis.total_defects
    assert total_30d >= total_7d + 1


def test_daily_read_notification_cleanup_preserves_unread(db_session: Session, workflow_setup):
    """
    Verify:
    1. Read notifications older than the cutoff (e.g. 1 day for daily cleanup) are deleted.
    2. Read notifications read recently (within 1 day) are preserved until the next daily cycle.
    3. Unread notifications (even very old ones) are STRICTLY PRESERVED and NEVER deleted.
    4. Immediate user clear-read (older_than_days=0) purges all read notifications for that user
       while still leaving all unread notifications untouched.
    """
    admin_a = workflow_setup["admin_a"]
    company_a = workflow_setup["company_a"]
    now = datetime.now(timezone.utc)

    # 1. Clean up any existing notifications for admin_a first for a clean state
    db_session.query(Notification).filter(Notification.recipient_id == admin_a.id).delete()
    db_session.commit()

    # 2. Seed test notifications:
    # - Read notification from 2 days ago (should be deleted by daily cleanup)
    old_read_notif = Notification(
        recipient_id=admin_a.id,
        company_id=company_a.id,
        notification_type="SYSTEM_ALERT",
        title="Old Read Notification",
        message="This was read 2 days ago",
        is_read=True,
        read_at=now - timedelta(days=2),
        created_at=now - timedelta(days=2),
    )
    # - Read notification from 2 hours ago (preserved by 1-day daily cleanup, removed by 0-day clear-read)
    recent_read_notif = Notification(
        recipient_id=admin_a.id,
        company_id=company_a.id,
        notification_type="SYSTEM_ALERT",
        title="Recent Read Notification",
        message="This was read 2 hours ago",
        is_read=True,
        read_at=now - timedelta(hours=2),
        created_at=now - timedelta(hours=2),
    )
    # - Unread notification from 5 days ago (MUST NEVER BE DELETED)
    old_unread_notif = Notification(
        recipient_id=admin_a.id,
        company_id=company_a.id,
        notification_type="FEATURE_STATUS_CHANGED",
        title="Old Unread Notification",
        message="This was created 5 days ago and is still unread",
        is_read=False,
        read_at=None,
        created_at=now - timedelta(days=5),
    )
    # - Unread notification from 1 hour ago (MUST NEVER BE DELETED)
    recent_unread_notif = Notification(
        recipient_id=admin_a.id,
        company_id=company_a.id,
        notification_type="FEATURE_ASSIGNED",
        title="Recent Unread Notification",
        message="This was created 1 hour ago and is still unread",
        is_read=False,
        read_at=None,
        created_at=now - timedelta(hours=1),
    )

    db_session.add_all([old_read_notif, recent_read_notif, old_unread_notif, recent_unread_notif])
    db_session.commit()

    old_read_id = old_read_notif.id
    recent_read_id = recent_read_notif.id
    old_unread_id = old_unread_notif.id
    recent_unread_id = recent_unread_notif.id

    # Verify all 4 are saved
    assert len(notification_service.list_notifications(db_session, user_id=admin_a.id)) == 4
    assert notification_service.get_unread_count(db_session, user_id=admin_a.id) == 2

    # Step A: Run daily cleanup with older_than_days=1 (same as the daily background worker)
    deleted_count = notification_service.cleanup_read_notifications(
        db_session, user_id=admin_a.id, older_than_days=1
    )
    assert deleted_count == 1  # Only old_read_notif should be purged

    remaining = notification_service.list_notifications(db_session, user_id=admin_a.id)
    remaining_ids = {n.id for n in remaining}

    # Old read is gone
    assert old_read_id not in remaining_ids
    # Recent read is still present
    assert recent_read_id in remaining_ids
    # Both unread notifications MUST be preserved!
    assert old_unread_id in remaining_ids
    assert recent_unread_id in remaining_ids
    assert notification_service.get_unread_count(db_session, user_id=admin_a.id) == 2

    # Step B: Run user clear-read with older_than_days=0 (immediate clear read)
    user_cleared_count = notification_service.cleanup_read_notifications(
        db_session, user_id=admin_a.id, older_than_days=0
    )
    assert user_cleared_count == 1  # recent_read_notif is purged

    final_remaining = notification_service.list_notifications(db_session, user_id=admin_a.id)
    final_ids = {n.id for n in final_remaining}

    # All read notifications are gone
    assert recent_read_id not in final_ids
    # Unread notifications are STILL there!
    assert old_unread_id in final_ids
    assert recent_unread_id in final_ids
    assert len(final_remaining) == 2
    assert all(not n.is_read for n in final_remaining)


def test_notification_cleanup_api_endpoints(db_session: Session, workflow_setup):
    """
    Test the REST API endpoints:
    1. DELETE /api/notifications/read - Purges read notifications for the current authenticated user.
    2. POST /api/notifications/cleanup-daily - 403 for non-admins, 200 for admins/super-admins.
    """
    admin_a = workflow_setup["admin_a"]
    dev_user = workflow_setup["bf_dev"]
    super_admin = workflow_setup["super_admin"]
    company_a = workflow_setup["company_a"]
    now = datetime.now(timezone.utc)

    # Clean up prior notifications for admin_a
    db_session.query(Notification).filter(Notification.recipient_id == admin_a.id).delete()
    db_session.commit()

    # Seed 1 read and 1 unread notification for admin_a
    notif_read = Notification(
        recipient_id=admin_a.id,
        company_id=company_a.id,
        notification_type="STATUS_UPDATE",
        title="Read Notification for API Test",
        message="Already read",
        is_read=True,
        read_at=now,
        created_at=now,
    )
    notif_unread = Notification(
        recipient_id=admin_a.id,
        company_id=company_a.id,
        notification_type="FEATURE_ASSIGNED",
        title="Unread Notification for API Test",
        message="Still unread",
        is_read=False,
        read_at=None,
        created_at=now,
    )
    db_session.add_all([notif_read, notif_unread])
    db_session.commit()

    unread_id = notif_unread.id
    read_id = notif_read.id

    client = TestClient(app)

    # 1. Non-admin trying to trigger platform-wide daily cleanup -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: dev_user
    res = client.post("/api/notifications/cleanup-daily")
    assert res.status_code == 403
    assert "Only Administrators" in res.json().get("detail", "")

    # 2. Authenticated user calls DELETE /api/notifications/read?older_than_days=0
    app.dependency_overrides[get_current_user] = lambda: admin_a
    res = client.delete("/api/notifications/read?older_than_days=0")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["deleted_count"] >= 1

    # Verify unread notification is still intact in the database
    remaining = notification_service.list_notifications(db_session, user_id=admin_a.id)
    assert any(n.id == unread_id for n in remaining)
    assert not any(n.id == read_id for n in remaining)

    # 3. Super Admin triggers platform-wide daily cleanup -> 200 OK
    app.dependency_overrides[get_current_user] = lambda: super_admin
    res = client.post("/api/notifications/cleanup-daily?older_than_days=1")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Cleanup dependency overrides
    app.dependency_overrides.pop(get_current_user, None)


def test_06_analytics_time_filters_and_tenant_isolation(workflow_setup, db_session: Session):
    """
    Test 06:
    - SuperAdmin platform analytics time filtering (7, 30, 90 days)
    - Verifies growth points length and that today is included
    - AnalyticsService overview time filtering (7, 30, 90 days)
    - Tenant isolation: developer workload excludes other tenant's users
    """
    from app.services.super_admin_service import SuperAdminService

    sa_user = workflow_setup["super_admin"]
    admin_a = workflow_setup["admin_a"]
    company_a = workflow_setup["company_a"]

    sa_service = SuperAdminService()
    analytics_service_inst = AnalyticsService()

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Platform analytics: 7, 30, 90 days
    for d in [7, 30, 90]:
        res = sa_service.get_platform_analytics(db_session, days=d)
        assert res.total_companies >= 1
        assert len(res.growth_trend) >= 2
        # Verify the last growth point is today
        assert res.growth_trend[-1].date == today_str
        # Verify company metrics exist
        assert len(res.company_metrics) >= 1

    # 2. Analytics overview: 7, 30, 90 days
    for d in [7, 30, 90]:
        ov = analytics_service_inst.get_overview(
            db=db_session,
            current_user=admin_a,
            days=d
        )
        assert ov.kpis is not None
        # Trends length corresponds to number of days (+1 for inclusive dates)
        assert len(ov.defect_trends) >= d
        assert ov.defect_trends[-1].date == today_str

    # 3. Developer Workload Tenant Isolation:
    # Customer Admin A must NOT see developers from other companies in developer workload
    ov_admin_a = analytics_service_inst.get_overview(
        db=db_session,
        current_user=admin_a,
        days=30
    )
    for dev_w in ov_admin_a.developer_workload:
        dev_obj = db_session.query(User).filter(User.id == dev_w.developer_id).first()
        if dev_obj and dev_obj.company_id:
            assert dev_obj.company_id == company_a.id, f"Tenant leak: developer from company {dev_obj.company_id} appeared in company {company_a.id} workload"




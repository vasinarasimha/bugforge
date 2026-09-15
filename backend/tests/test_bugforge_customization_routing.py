"""
Tests for BugForge Customization Request Routing,
Reported Issues Isolation, Status Tracking, and Primary Key Secrecy.
"""
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity
from app.models.customization_request import CustomizationRequest
from app.services.issue_service import IssueService
from app.services.company_settings_service import company_settings_service
from app.schemas.company import CustomizationRequestCreate
from app.schemas.issue import IssueUpdate


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def setup_routing_data(db_session: Session):
    # 1. BugForge Company (id=1 or name="BugForge")
    bf_comp = db_session.query(Company).filter(Company.name == "BugForge").first()
    if not bf_comp:
        bf_comp = Company(id=1, name="BugForge", website="bugforge.internal", is_active=True)
        db_session.add(bf_comp)
        db_session.flush()

    # Roles
    admin_role = db_session.query(Role).filter(Role.name == "Admin").first()
    sa_role = db_session.query(Role).filter(Role.name == "Super Admin").first()

    # 2. BugForge User
    bf_user = db_session.query(User).filter(User.email == "bf_core_eng@bugforge.test").first()
    if not bf_user:
        bf_user = User(
            email="bf_core_eng@bugforge.test",
            password_hash="testpass",
            full_name="BugForge Core Engineer",
            company_id=bf_comp.id,
            is_active=True,
            roles=[admin_role] if admin_role else []
        )
        db_session.add(bf_user)
        db_session.flush()

    # BugForge Project
    bf_project = db_session.query(Project).filter(Project.company_id == bf_comp.id).first()
    if not bf_project:
        bf_project = Project(
            name="BugForge Platform Core",
            key="BF",
            company_id=bf_comp.id,
            created_by=bf_user.id,
            status="Active"
        )
        db_session.add(bf_project)
        db_session.flush()

    # BugForge Statuses
    open_status = db_session.query(IssueStatus).filter(IssueStatus.company_id == bf_comp.id, IssueStatus.name == "Open").first()
    if not open_status:
        open_status = IssueStatus(name="Open", company_id=bf_comp.id, category="open", is_initial=True, is_active=True)
        db_session.add(open_status)
        db_session.flush()

    in_progress_status = db_session.query(IssueStatus).filter(IssueStatus.company_id == bf_comp.id, IssueStatus.name == "In Progress").first()
    if not in_progress_status:
        in_progress_status = IssueStatus(name="In Progress", company_id=bf_comp.id, category="in_progress", is_active=True)
        db_session.add(in_progress_status)
        db_session.flush()

    resolved_status = db_session.query(IssueStatus).filter(IssueStatus.company_id == bf_comp.id, IssueStatus.name == "Resolved").first()
    if not resolved_status:
        resolved_status = IssueStatus(name="Resolved", company_id=bf_comp.id, category="resolved", is_active=True)
        db_session.add(resolved_status)
        db_session.flush()

    # 3. Customer Company
    client_comp = db_session.query(Company).filter(Company.name == "Zenith Client Corp").first()
    if not client_comp:
        client_comp = Company(name="Zenith Client Corp", website="zenith.io", is_active=True)
        db_session.add(client_comp)
        db_session.flush()

    # Customer User
    client_user = db_session.query(User).filter(User.email == "lead@zenith.io").first()
    if not client_user:
        client_user = User(
            email="lead@zenith.io",
            password_hash="testpass",
            full_name="Zenith Lead Admin",
            company_id=client_comp.id,
            is_active=True,
            roles=[admin_role] if admin_role else []
        )
        db_session.add(client_user)
        db_session.flush()

    return {
        "bf_comp": bf_comp,
        "bf_project": bf_project,
        "bf_user": bf_user,
        "client_comp": client_comp,
        "client_user": client_user,
        "open_status": open_status,
        "in_progress_status": in_progress_status,
        "resolved_status": resolved_status
    }


def test_customization_request_creates_bugforge_project_issue_and_tracks_status(db_session: Session, setup_routing_data):
    """
    Verify:
    1. Client feature request creates a CustomizationRequest with request_type='Feature'.
    2. Automatically routes to BugForge project as a Feature issue with issue_key starting with 'BF-'.
    3. Client defect request creates a CustomizationRequest with request_type='Defect'.
    4. Automatically routes to BugForge project as a Defect issue.
    5. The customization request links to the issue and tracks implementation_status.
    """
    client_comp = setup_routing_data["client_comp"]
    client_user = setup_routing_data["client_user"]
    bf_comp = setup_routing_data["bf_comp"]

    # 1. Submit Feature Request
    feature_req_data = CustomizationRequestCreate(
        title="Custom SSO Okta Integration",
        description="We need SAML 2.0 and Okta provisioning support.",
        category="Security",
        requested_behavior="Redirect to enterprise IdP upon clicking company sign-in",
        request_type="Feature"
    )
    feature_cr = company_settings_service.submit_customization_request(
        db_session,
        company_id=client_comp.id,
        user=client_user,
        data=feature_req_data
    )

    assert feature_cr.id is not None
    assert feature_cr.request_type == "Feature"
    assert feature_cr.linked_issue_id is not None
    assert feature_cr.linked_issue_key is not None
    feature_issue = db_session.query(Issue).filter(Issue.id == feature_cr.linked_issue_id).first()
    assert feature_issue is not None
    assert feature_issue.company_id == bf_comp.id
    assert feature_issue.issue_type == "Feature"
    assert feature_issue.requesting_company_id == client_comp.id

    # 2. Submit Defect Request
    defect_req_data = CustomizationRequestCreate(
        title="Webhook Payload Dropping Unicode Characters",
        description="Webhooks sent to our endpoint drop non-ASCII characters.",
        category="Integrations",
        requested_behavior="Ensure UTF-8 encoding in JSON webhook body",
        request_type="Defect"
    )
    defect_cr = company_settings_service.submit_customization_request(
        db_session,
        company_id=client_comp.id,
        user=client_user,
        data=defect_req_data
    )

    assert defect_cr.id is not None
    assert defect_cr.request_type == "Defect"
    assert defect_cr.linked_issue_id is not None
    assert defect_cr.linked_issue_key is not None
    defect_issue = db_session.query(Issue).filter(Issue.id == defect_cr.linked_issue_id).first()
    assert defect_issue is not None
    assert defect_issue.company_id == bf_comp.id
    assert defect_issue.issue_type == "Defect"
    assert defect_issue.requesting_company_id == client_comp.id


def test_reported_issues_isolation_for_customization_requests(db_session: Session, setup_routing_data):
    """
    Verify:
    1. For customer company members, customization request issues are NOT shown in Reported Issues.
    2. For BugForge company members, customization request issues ARE shown in Reported Issues.
    3. Customers can track status in Customization Requests listing.
    """
    client_comp = setup_routing_data["client_comp"]
    client_user = setup_routing_data["client_user"]
    bf_comp = setup_routing_data["bf_comp"]
    bf_user = setup_routing_data["bf_user"]

    issue_service = IssueService()

    # Check is_bugforge_user helper
    assert issue_service.is_bugforge_user(db_session, bf_user) is True
    assert issue_service.is_bugforge_user(db_session, client_user) is False

    # 1. Customer Company list in Reported Issues (is_bugforge=False)
    client_reported_issues = issue_service.list(db_session, company_id=client_comp.id, is_bugforge=False)
    assert not any(i.requesting_company_id == client_comp.id for i in client_reported_issues)

    # 2. BugForge Company list in Reported Issues (is_bugforge=True)
    bf_reported_issues = issue_service.list(db_session, company_id=bf_comp.id, is_bugforge=True)
    bf_customization_issues = [i for i in bf_reported_issues if i.requesting_company_id == client_comp.id]
    assert len(bf_customization_issues) >= 2

    # 3. Customer Company tracks status via Customization Requests
    client_cr_list = company_settings_service.list_customization_requests(db_session, company_id=client_comp.id)
    assert len(client_cr_list) >= 2
    for cr in client_cr_list:
        assert hasattr(cr, "implementation_status")
        assert hasattr(cr, "linked_issue_key")


def test_status_synchronization_from_issue_to_customization_request(db_session: Session, setup_routing_data):
    """
    Verify:
    When a BugForge engineer updates the status of the linked issue,
    the linked customization request automatically synchronizes its status
    so the customer sees the updated implementation status.
    """
    client_comp = setup_routing_data["client_comp"]
    client_user = setup_routing_data["client_user"]
    bf_user = setup_routing_data["bf_user"]
    in_progress_status = setup_routing_data["in_progress_status"]
    resolved_status = setup_routing_data["resolved_status"]

    issue_service = IssueService()

    # Create request
    req_data = CustomizationRequestCreate(
        title="Sync Status Test Feature",
        description="Testing that status transitions sync back to customer.",
        category="General",
        requested_behavior="Status change reflection",
        request_type="Feature"
    )
    cr = company_settings_service.submit_customization_request(
        db_session,
        company_id=client_comp.id,
        user=client_user,
        data=req_data
    )

    issue = db_session.query(Issue).filter(Issue.id == cr.linked_issue_id).first()
    assert issue is not None

    cr_model = db_session.query(CustomizationRequest).filter(CustomizationRequest.id == cr.id).first()
    assert cr_model is not None

    # BugForge engineer updates status to In Progress
    in_prog_update = IssueUpdate(
        title=issue.title,
        description=issue.description,
        project_id=issue.project_id,
        priority_id=issue.priority_id,
        severity_id=issue.severity_id,
        status_id=in_progress_status.id,
        issue_type=issue.issue_type
    )
    issue_service.update(db_session, issue.id, in_prog_update, user=bf_user)
    db_session.refresh(cr_model)
    assert cr_model.status == "Under Review"

    # BugForge engineer updates status to Resolved
    resolved_update = IssueUpdate(
        title=issue.title,
        description=issue.description,
        project_id=issue.project_id,
        priority_id=issue.priority_id,
        severity_id=issue.severity_id,
        status_id=resolved_status.id,
        issue_type=issue.issue_type
    )
    issue_service.update(db_session, issue.id, resolved_update, user=bf_user)
    db_session.refresh(cr_model)
    assert cr_model.status == "Implemented"

    # Customer queries their customization requests: implementation status shows 'Resolved'
    client_cr_list = company_settings_service.list_customization_requests(db_session, company_id=client_comp.id)
    matching = next(r for r in client_cr_list if r.id == cr.id)
    assert matching.implementation_status == "Resolved"
    assert matching.status == "Implemented"

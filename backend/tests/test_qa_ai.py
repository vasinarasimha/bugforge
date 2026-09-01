import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User

client = TestClient(app)


@pytest.fixture
def mock_auth():
    from app.api.dependencies.auth import get_current_user
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "qa_user@bugforge.com"
    mock_user.full_name = "QA Engineer"
    mock_role = MagicMock()
    mock_role.name = "QA"
    mock_user.roles = [mock_role]
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.pop(get_current_user, None)


def test_generate_test_cases_unauthorized():
    # Without mock_auth, request should return 401 or 403
    response = client.post("/api/ai/test-cases", json={"issue_id": 1})
    assert response.status_code in (401, 403)


def test_generate_test_cases_forbidden_for_developer():
    from app.api.dependencies.auth import get_current_user
    mock_user = MagicMock(spec=User)
    mock_user.id = 2
    mock_user.email = "dev@bugforge.com"
    mock_role = MagicMock()
    mock_role.name = "Developer"
    mock_user.roles = [mock_role]
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.post("/api/ai/test-cases", json={"issue_id": 1})
        assert response.status_code == 403
        assert "You do not have permission" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_detect_missing_scenarios_forbidden_for_reporter():
    from app.api.dependencies.auth import get_current_user
    mock_user = MagicMock(spec=User)
    mock_user.id = 3
    mock_user.email = "reporter@bugforge.com"
    mock_role = MagicMock()
    mock_role.name = "Reporter"
    mock_user.roles = [mock_role]
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.post("/api/ai/missing-scenarios", json={"issue_id": 1})
        assert response.status_code == 403
        assert "You do not have permission" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_generate_test_cases_issue_not_found(mock_auth):

    with patch('app.api.routes.ai.IssueRepository') as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get.return_value = None

        response = client.post("/api/ai/test-cases", json={"issue_id": 9999})
        assert response.status_code == 404
        assert "Issue not found" in response.json()["detail"]


def test_generate_test_cases_success(mock_auth):
    with patch('app.api.routes.ai.IssueRepository') as MockRepo, \
         patch('app.api.routes.ai.llm_service') as mock_llm_svc:

        mock_repo = MockRepo.return_value
        mock_issue = MagicMock()
        mock_issue.id = 10
        mock_issue.issue_key = "BF-10"
        mock_issue.title = "Login button unresponsive on mobile"
        mock_issue.description = "Tapping login on iOS Safari does nothing."
        mock_issue.reproduction_steps = "1. Open mobile browser. 2. Tap login."
        mock_issue.expected_behavior = "User is logged in."
        mock_issue.actual_behavior = "Button remains unresponsive."
        mock_issue.severity = MagicMock(name="Major")
        mock_issue.priority = MagicMock(name="High")
        mock_issue.status = MagicMock(name="Open")
        mock_issue.category = MagicMock(name="UI")
        mock_issue.module = MagicMock(name="Auth")
        mock_issue.project = MagicMock(name="BugForge Web")
        mock_issue.environment = "Production"
        mock_issue.browser = "Safari 17"
        mock_issue.operating_system = "iOS 17"
        mock_issue.ai_root_cause_session_id = None
        mock_repo.get.return_value = mock_issue

        mock_llm_svc.generate_test_cases.return_value = {
            "summary": {
                "total_count": 4,
                "by_type": {
                    "Positive / Functional": 1,
                    "Negative / Validation": 1,
                    "Boundary / Edge": 1,
                    "Regression": 1
                },
                "overview": "Comprehensive mobile authentication test suite."
            },
            "test_cases": [
                {
                    "test_case_id": "TC-001",
                    "scenario": "Verify standard mobile login on Safari",
                    "test_type": "Positive / Functional",
                    "priority": "High",
                    "preconditions": "Valid user account exists",
                    "steps": ["Navigate to login", "Enter credentials", "Tap Login button"],
                    "test_data": "user: test@example.com",
                    "expected_result": "Dashboard loads successfully"
                },
                {
                    "test_case_id": "TC-002",
                    "scenario": "Verify touch event handling with rapid double-tap",
                    "test_type": "Boundary / Edge",
                    "priority": "Medium",
                    "preconditions": "Mobile device connected",
                    "steps": ["Tap login button rapidly twice"],
                    "test_data": "N/A",
                    "expected_result": "Single login request dispatched without freezing"
                }
            ]
        }

        response = client.post("/api/ai/test-cases", json={"issue_id": 10})
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert data["summary"]["total_count"] == 4
        assert len(data["test_cases"]) == 2
        assert data["test_cases"][0]["test_case_id"] == "TC-001"


def test_detect_missing_scenarios_success(mock_auth):
    with patch('app.api.routes.ai.IssueRepository') as MockRepo, \
         patch('app.api.routes.ai.llm_service') as mock_llm_svc:

        mock_repo = MockRepo.return_value
        mock_issue = MagicMock()
        mock_issue.id = 10
        mock_issue.issue_key = "BF-10"
        mock_issue.title = "Checkout totals calculate incorrectly with discount coupon"
        mock_issue.description = "Applying 10% coupon results in negative subtotal."
        mock_issue.reproduction_steps = "1. Add item. 2. Apply coupon."
        mock_issue.expected_behavior = "10% deducted."
        mock_issue.actual_behavior = "Negative balance."
        mock_issue.severity = MagicMock(name="Critical")
        mock_issue.priority = MagicMock(name="Critical")
        mock_issue.status = MagicMock(name="In Progress")
        mock_issue.ai_root_cause_session_id = None
        mock_repo.get.return_value = mock_issue

        mock_llm_svc.detect_missing_scenarios.return_value = {
            "already_covered_summary": ["Single coupon code applied on standard cart"],
            "missing_scenarios": [
                {
                    "scenario": "Coupon application when cart total is zero or free trial items present",
                    "why_it_matters": "Floating point math could crash pricing engine or lead to negative invoice",
                    "risk": "High",
                    "suggested_test": "Add zero dollar items, apply coupon code, verify minimum total is clamped at 0.00",
                    "priority": "High"
                },
                {
                    "scenario": "Concurrent coupon application across multiple browser tabs",
                    "why_it_matters": "Race condition may allow double redemption of single-use coupon",
                    "risk": "Medium",
                    "suggested_test": "Open two tabs and submit apply coupon simultaneously",
                    "priority": "Medium"
                }
            ],
            "disclaimer": "These recommendations are AI-identified coverage gaps to assist QA testing and do not guarantee complete test coverage."
        }

        response = client.post("/api/ai/missing-scenarios", json={
            "issue_id": 10,
            "existing_test_cases": [{"test_case_id": "TC-001", "scenario": "Basic coupon test"}]
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["missing_scenarios"]) == 2
        assert data["missing_scenarios"][0]["risk"] == "High"
        assert "disclaimer" in data

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


def test_generate_test_cases_when_llm_omits_test_cases(mock_auth):
    """Regression test: LLM response contains ONLY 'summary' (e.g. truncated output). Must not fail with 500."""
    with patch('app.api.routes.ai.IssueRepository') as MockRepo, \
         patch('app.api.routes.ai.llm_service') as mock_llm_svc:

        mock_repo = MockRepo.return_value
        mock_issue = MagicMock()
        mock_issue.id = 10
        mock_repo.get.return_value = mock_issue

        # This was the exact payload that previously crashed FastAPI with ResponseValidationError
        mock_llm_svc.generate_test_cases.return_value = {
            "summary": {
                "total_count": 10,
                "by_type": {
                    "Positive / Functional": 3,
                    "Negative / Validation": 3,
                    "Boundary / Edge": 2,
                    "Regression": 2
                },
                "overview": "The test suite covers critical payment flow, ensuring stability, validation, boundary handling, and regression."
            }
        }

        response = client.post("/api/ai/test-cases", json={"issue_id": 10})
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "test_cases" in data
        assert isinstance(data["test_cases"], list)


def test_generate_test_cases_normalizes_dict_test_data_and_string_steps(mock_auth):
    """Ensure dict test_data and string steps are cleanly handled without ValidationError."""
    with patch('app.api.routes.ai.IssueRepository') as MockRepo, \
         patch('app.api.routes.ai.llm_service') as mock_llm_svc:

        mock_repo = MockRepo.return_value
        mock_issue = MagicMock()
        mock_issue.id = 10
        mock_repo.get.return_value = mock_issue

        mock_llm_svc.generate_test_cases.return_value = {
            "summary": {
                "total_count": 1,
                "by_type": {"Positive / Functional": 1},
                "overview": "Overview"
            },
            "test_cases": [
                {
                    "test_case_id": "TC-001",
                    "scenario": "Verify payment payload",
                    "test_type": "Positive / Functional",
                    "priority": "High",
                    "preconditions": "Precondition",
                    "steps": "1. Enter card\n2. Click submit",  # String instead of list
                    "test_data": {"card_number": "4111111111111111", "cvv": 123},  # Dict instead of str
                    "expected_result": "Success"
                }
            ]
        }

        response = client.post("/api/ai/test-cases", json={"issue_id": 10})
        assert response.status_code == 200
        data = response.json()
        tc = data["test_cases"][0]
        assert isinstance(tc["steps"], list)
        assert len(tc["steps"]) == 2
        assert isinstance(tc["test_data"], str)
        assert "4111111111111111" in tc["test_data"]


def test_llm_service_normalization_synthesizes_baseline_when_empty():
    """Unit test: llm_service._normalize_test_cases_response produces baseline test cases if LLM returns only summary."""
    from app.services.llm_service import llm_service

    raw_data = {
        "summary": {
            "total_count": 10,
            "by_type": {"Positive / Functional": 3},
            "overview": "Overview from AI"
        }
    }
    defect = {
        "title": "Payment form crashes on submit",
        "priority_name": "Critical",
        "reproduction_steps": "1. Fill form\n2. Click submit",
        "expected_behavior": "Payment processed"
    }

    result = llm_service._normalize_test_cases_response(raw_data, defect)
    assert "test_cases" in result
    assert len(result["test_cases"]) == 4
    assert result["summary"]["total_count"] == 4
    assert result["summary"]["overview"] == "Overview from AI"
    assert result["test_cases"][0]["test_type"] == "Positive / Functional"
    assert result["test_cases"][1]["test_type"] == "Negative / Validation"


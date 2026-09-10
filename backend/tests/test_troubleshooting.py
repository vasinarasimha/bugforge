import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.services.hf_service import hf_service

client = TestClient(app)


@pytest.fixture
def mock_auth():
    from app.api.dependencies.auth import get_current_user
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.company_id = 1
    mock_user.email = "reporter@bugforge.com"
    mock_user.full_name = "Reporter User"
    mock_user.roles = []
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def sample_payload():
    return {
        "title": "Cannot save defect with attachments",
        "description": "When clicking Save after uploading an image, the page shows a warning and fails to save.",
        "project_id": 1,
        "priority_id": 1,
        "severity_id": 1,
        "status_id": 1,
        "environment": "Production",
        "browser": "Chrome 120",
    }


# ── Test 1: Start Session ──

@patch("app.services.troubleshooting_service.hf_service")
def test_start_troubleshooting(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"
    mock_hf.generate_troubleshooting_response.return_value = {
        "status": "question",
        "question_number": 1,
        "question": "Did an error message appear on screen after clicking Save?",
        "question_type": "multiple_choice",
        "options": [
            {"id": "A", "label": "Yes, an error message appeared"},
            {"id": "B", "label": "No, the screen kept spinning"},
            {"id": "C", "label": "I am not sure"},
        ],
        "candidate_root_causes": [
            {"cause": "Upload file size exceeded max limit", "confidence": 0.50},
            {"cause": "Session token expired", "confidence": 0.30},
        ],
    }

    response = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "questioning"
    assert data["question_number"] == 1
    assert "error message" in data["question"]
    assert len(data["options"]) == 3


# ── Test 2: Submit Answer Moves to Question 2 ──

@patch("app.services.troubleshooting_service.hf_service")
def test_submit_answer_success(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"
    mock_hf.generate_troubleshooting_response.side_effect = [
        # Start -> Q1
        {
            "status": "question",
            "question_number": 1,
            "question": "Did an error popup appear?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Yes"}, {"id": "B", "label": "No"}],
            "candidate_root_causes": [{"cause": "File too large", "confidence": 0.40}],
        },
        # Answer Q1 -> Q2
        {
            "status": "question",
            "question_number": 2,
            "question": "What did the error message say?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "A", "label": "File size exceeds 10MB limit"},
                {"id": "B", "label": "Server unavailable"},
                {"id": "C", "label": "I don't remember"},
            ],
            "candidate_root_causes": [{"cause": "File too large", "confidence": 0.70}],
        },
    ]

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    ans_res = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 1, "answer": "A: Yes"},
    )
    assert ans_res.status_code == 200
    data = ans_res.json()
    assert data["status"] == "questioning"
    assert data["question_number"] == 2
    assert "What did the error message say" in data["question"]


# ── Test 3: Early Root-Cause Confirmation (e.g. after Q2) ──

@patch("app.services.troubleshooting_service.hf_service")
def test_early_root_cause_confirmation(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"
    mock_hf.generate_troubleshooting_response.side_effect = [
        # Start -> Q1
        {
            "status": "question",
            "question_number": 1,
            "question": "Did the error say file size exceeded?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Yes"}, {"id": "B", "label": "No"}],
            "candidate_root_causes": [{"cause": "Upload limit", "confidence": 0.60}],
        },
        # Answer Q1 -> Confirmed!
        {
            "status": "confirmed",
            "question_number": 1,
            "root_cause": "The uploaded attachment exceeded the 10MB nginx client body size limit, causing the reverse proxy to reject the payload with 413 Payload Too Large.",
            "confidence": 0.95,
            "evidence": ["Reporter confirmed the error popup stated file size exceeded limit."],
            "recommended_fix": "Increase client_max_body_size in nginx configuration and add client-side file size validation before upload.",
            "next_diagnostic_step": None,
        },
    ]

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    session_id = start_res.json()["session_id"]

    ans_res = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 1, "answer": "A: Yes"},
    )
    assert ans_res.status_code == 200
    data = ans_res.json()
    assert data["status"] == "confirmed"
    assert "nginx client body size limit" in data["root_cause"]
    assert data["confidence"] == 0.95
    assert len(data["evidence"]) >= 1


# ── Test 4: Nine-Question Flow Generates Question 10 ──

@patch("app.services.troubleshooting_service.hf_service")
def test_nine_question_to_ten_flow(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"

    # Mock sequence: Start -> Q1, then Q1..Q8 -> Q2..Q9, then Q9 -> Q10
    responses = [
        {
            "status": "question",
            "question_number": i,
            "question": f"Diagnostic question #{i}?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Option A"}, {"id": "B", "label": "Option B"}],
            "candidate_root_causes": [{"cause": f"Hypothesis {i}", "confidence": 0.1 * i}],
        }
        for i in range(1, 11)
    ]
    mock_hf.generate_troubleshooting_response.side_effect = responses

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    session_id = start_res.json()["session_id"]

    # Submit answers 1 through 8
    for q_num in range(1, 9):
        res = client.post(
            f"/api/ai/troubleshooting/{session_id}/answer",
            json={"question_number": q_num, "answer": "A: Option A"},
        )
        assert res.status_code == 200
        assert res.json()["question_number"] == q_num + 1

    # Now on Question 9, submit Answer 9
    ans9_res = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 9, "answer": "A: Option A"},
    )
    assert ans9_res.status_code == 200
    data = ans9_res.json()
    # Question 10 must be generated successfully without 503 or error!
    assert data["status"] == "questioning"
    assert data["question_number"] == 10
    assert data["question"] == "Diagnostic question #10?"


# ── Test 5: Ten-Question Hard Limit Forces Conclusion (Never Question 11) ──

@patch("app.services.troubleshooting_service.hf_service")
def test_ten_question_hard_limit_forces_conclusion(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"

    responses = [
        {
            "status": "question",
            "question_number": i,
            "question": f"Diagnostic question #{i}?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Option A"}, {"id": "B", "label": "Option B"}],
            "candidate_root_causes": [{"cause": f"Hypothesis {i}", "confidence": 0.05 * i}],
        }
        for i in range(1, 11)
    ]
    # On answer 10: conclusion
    responses.append({
        "status": "insufficient_evidence",
        "question_number": 10,
        "root_cause": "Intermittent network latency or unhandled edge-case timeout during attachment upload.",
        "confidence": 0.55,
        "evidence": ["User observed intermittent upload failures"],
        "recommended_fix": "Add telemetry and retry on HTTP timeout.",
        "next_diagnostic_step": "Check application load balancer logs.",
    })
    mock_hf.generate_troubleshooting_response.side_effect = responses

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    session_id = start_res.json()["session_id"]

    for q_num in range(1, 10):
        client.post(
            f"/api/ai/troubleshooting/{session_id}/answer",
            json={"question_number": q_num, "answer": "A: Option A"},
        )

    # Submit 10th answer
    ans10_res = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 10, "answer": "A: Option A"},
    )
    assert ans10_res.status_code == 200
    data = ans10_res.json()
    assert data["status"] in ("confirmed", "insufficient_evidence")
    assert "Intermittent network latency" in data["root_cause"]
    assert data["question_number"] == 10
    # Verified: NO Question 11 is ever generated


# ── Test 6: AI Failure on Question 9 Does NOT Corrupt State ──

@patch("app.services.troubleshooting_service.hf_service")
def test_ai_failure_on_question_9_does_not_corrupt_state(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"

    responses = [
        {
            "status": "question",
            "question_number": i,
            "question": f"Diagnostic question #{i}?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Option A"}, {"id": "B", "label": "Option B"}],
            "candidate_root_causes": [{"cause": f"Hypothesis {i}", "confidence": 0.05 * i}],
        }
        for i in range(1, 10)
    ]
    mock_hf.generate_troubleshooting_response.side_effect = responses

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    session_id = start_res.json()["session_id"]

    # Answer questions 1 through 8
    for q_num in range(1, 9):
        client.post(
            f"/api/ai/troubleshooting/{session_id}/answer",
            json={"question_number": q_num, "answer": "A: Option A"},
        )

    # Check session state: question_count should be 8
    session_res = client.get(f"/api/ai/troubleshooting/{session_id}")
    assert session_res.status_code == 200
    assert session_res.json()["question_count"] == 8

    # Now make the AI call fail on Question 9
    mock_hf.generate_troubleshooting_response.side_effect = ValueError(
        "AI conclusion response missing 'root_cause'"
    )

    ans9_fail_res = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 9, "answer": "A: Option A"},
    )
    # Must return 503
    assert ans9_fail_res.status_code == 503

    # Check session state again: question_count MUST STILL BE 8!
    session_check = client.get(f"/api/ai/troubleshooting/{session_id}")
    assert session_check.status_code == 200
    assert session_check.json()["question_count"] == 8
    assert session_check.json()["status"] == "questioning"

    # Now retry submitting Question 9 with a working AI
    mock_hf.generate_troubleshooting_response.side_effect = None
    mock_hf.generate_troubleshooting_response.return_value = {
        "status": "question",
        "question_number": 10,
        "question": "Diagnostic question #10?",
        "question_type": "multiple_choice",
        "options": [{"id": "A", "label": "Option A"}, {"id": "B", "label": "Option B"}],
        "candidate_root_causes": [{"cause": "Final hypothesis", "confidence": 0.80}],
    }

    ans9_retry_res = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 9, "answer": "A: Option A"},
    )
    # Retry succeeds without conflict (not 409)!
    assert ans9_retry_res.status_code == 200
    assert ans9_retry_res.json()["question_number"] == 10


# ── Test 7: Duplicate Submit Idempotency ──

@patch("app.services.troubleshooting_service.hf_service")
def test_duplicate_submit_idempotency(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"
    mock_hf.generate_troubleshooting_response.side_effect = [
        # Start -> Q1
        {
            "status": "question",
            "question_number": 1,
            "question": "Question 1?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Yes"}, {"id": "B", "label": "No"}],
            "candidate_root_causes": [],
        },
        # Q1 -> Q2
        {
            "status": "question",
            "question_number": 2,
            "question": "Question 2?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Yes"}, {"id": "B", "label": "No"}],
            "candidate_root_causes": [],
        },
    ]

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    session_id = start_res.json()["session_id"]

    # First submit
    res1 = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 1, "answer": "A: Yes"},
    )
    assert res1.status_code == 200
    assert res1.json()["question_number"] == 2

    # Second submit (duplicate click for Q1)
    res2 = client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 1, "answer": "A: Yes"},
    )
    # Returns current question state idempotently
    assert res2.status_code == 200
    assert res2.json()["question_number"] == 2


# ── Test 8: AI Response Normalization Unit Tests ──

def test_ai_response_normalization():
    # Test 1: Model uses 'suspected_cause' instead of 'root_cause'
    parsed_with_suspected = {
        "status": "insufficient_evidence",
        "suspected_cause": "Network gateway timeout",
        "confidence": 0.60,
    }
    normalized = hf_service._validate_response(parsed_with_suspected, expected_question_number=10, is_final_conclusion=True)
    assert normalized["status"] == "insufficient_evidence"
    assert normalized["root_cause"] == "Network gateway timeout"
    assert normalized["confidence"] == 0.60

    # Test 2: Model returns options as string list
    parsed_with_str_options = {
        "status": "question",
        "question": "Did the page crash?",
        "question_type": "multiple_choice",
        "options": ["Yes, completely blank", "No, error dialog shown"],
    }
    norm_q = hf_service._validate_response(parsed_with_str_options, expected_question_number=1, is_final_conclusion=False)
    assert norm_q["status"] == "question"
    assert len(norm_q["options"]) == 2
    assert norm_q["options"][0]["id"] == "A"
    assert norm_q["options"][0]["label"] == "Yes, completely blank"

    # Test 3: Model returns question on final step -> automatically converts to insufficient_evidence
    parsed_question_on_final = {
        "status": "question",
        "question": "One more thing?",
        "candidate_root_causes": [{"cause": "Database connection pool exhausted", "confidence": 0.65}],
    }
    norm_final = hf_service._validate_response(parsed_question_on_final, expected_question_number=10, is_final_conclusion=True)
    assert norm_final["status"] == "insufficient_evidence"
    assert norm_final["root_cause"] == "Database connection pool exhausted"


# ── Test 9: Confirm and Create Issue ──

@patch("app.services.troubleshooting_service.hf_service")
def test_confirm_and_create_issue(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"
    mock_hf.generate_troubleshooting_response.side_effect = [
        # Start -> Q1
        {
            "status": "question",
            "question_number": 1,
            "question": "Did it crash?",
            "question_type": "multiple_choice",
            "options": [{"id": "A", "label": "Yes"}, {"id": "B", "label": "No"}],
            "candidate_root_causes": [],
        },
        # Q1 -> Confirmed
        {
            "status": "confirmed",
            "question_number": 1,
            "root_cause": "Nginx client body size limit (10MB)",
            "confidence": 0.92,
            "evidence": ["User uploaded 15MB file"],
            "recommended_fix": "Increase client_max_body_size to 25MB",
        },
    ]

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    session_id = start_res.json()["session_id"]

    client.post(
        f"/api/ai/troubleshooting/{session_id}/answer",
        json={"question_number": 1, "answer": "A: Yes"},
    )

    with patch("app.services.issue_service.ProjectRepository") as MockProjectRepo, \
         patch("app.services.issue_service.IssueRepository") as MockIssueRepo:
        mock_proj = MagicMock()
        mock_proj.id = 1
        mock_proj.key = "TEST"
        mock_proj.company_id = 1
        mock_proj.lead_id = 1
        mock_proj.members = []
        MockProjectRepo.return_value.get.return_value = mock_proj

        mock_created_issue = MagicMock()
        mock_created_issue.id = 42
        mock_created_issue.issue_key = "TEST-42"
        mock_created_issue.embedding_vector = None
        mock_created_issue.project_id = 1
        MockIssueRepo.return_value.create.return_value = mock_created_issue

        # Confirm and create issue
        confirm_res = client.post(
            f"/api/ai/troubleshooting/{session_id}/confirm",
            json={"title": "Custom confirmed title"},
        )
        assert confirm_res.status_code == 200
        confirm_data = confirm_res.json()
        assert confirm_data["status"] == "completed"
        assert confirm_data["issue_id"] == 42
        assert confirm_data["issue_key"] == "TEST-42"
        assert confirm_data["root_cause"] == "Nginx client body size limit (10MB)"



# ── Test 10: Cancel Session ──

@patch("app.services.troubleshooting_service.hf_service")
def test_cancel_troubleshooting_session(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"
    mock_hf.generate_troubleshooting_response.return_value = {
        "status": "question",
        "question_number": 1,
        "question": "Did it crash?",
        "question_type": "multiple_choice",
        "options": [{"id": "A", "label": "Yes"}, {"id": "B", "label": "No"}],
        "candidate_root_causes": [],
    }

    start_res = client.post("/api/ai/troubleshooting/start", json=sample_payload)
    session_id = start_res.json()["session_id"]

    cancel_res = client.post(f"/api/ai/troubleshooting/{session_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


# ── Test 11: Reject Non-Bug Issue Types ──

def test_troubleshooting_rejects_task_and_feature(mock_auth, sample_payload):
    task_payload = {**sample_payload, "issue_type": "Task"}
    res_task = client.post("/api/ai/troubleshooting/start", json=task_payload)
    assert res_task.status_code in (400, 422)

    feature_payload = {**sample_payload, "issue_type": "Feature"}
    res_feature = client.post("/api/ai/troubleshooting/start", json=feature_payload)
    assert res_feature.status_code in (400, 422)


@patch("app.services.troubleshooting_service.hf_service")
def test_troubleshooting_accepts_bug_and_defect(mock_hf, mock_auth, sample_payload):
    mock_hf.is_available = True
    mock_hf.model = "Qwen/Qwen3-Coder-Next"
    mock_hf.generate_troubleshooting_response.return_value = {
        "status": "question",
        "question_number": 1,
        "question": "Did you verify?",
        "question_type": "multiple_choice",
        "options": [{"id": "A", "label": "Yes"}, {"id": "B", "label": "No"}],
        "candidate_root_causes": [],
    }

    bug_payload = {**sample_payload, "issue_type": "Bug"}
    res_bug = client.post("/api/ai/troubleshooting/start", json=bug_payload)
    assert res_bug.status_code == 200

    defect_payload = {**sample_payload, "issue_type": "Defect"}
    res_defect = client.post("/api/ai/troubleshooting/start", json=defect_payload)
    assert res_defect.status_code == 200


"""
Pydantic schemas for the AI troubleshooting / root-cause analysis feature.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request Schemas ──

class TroubleshootingStartRequest(BaseModel):
    """Defect draft data to start a troubleshooting session."""
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    project_id: int = Field(gt=0)
    priority_id: int = Field(gt=0)
    severity_id: int = Field(gt=0)
    status_id: int = Field(gt=0)
    issue_type: str = "Defect"
    category_id: int | None = Field(default=None, gt=0)
    module_id: int | None = Field(default=None, gt=0)
    assigned_to: int | None = Field(default=None, gt=0)
    environment: str | None = None
    browser: str | None = None
    operating_system: str | None = None
    reproduction_steps: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    sprint_id: int | None = None

    @field_validator('issue_type')
    @classmethod
    def validate_issue_type(cls, v: str) -> str:
        if v not in ("Bug", "Defect"):
            raise ValueError(f"AI Root-Cause Analysis is only available for Bug/Defect issue types (got '{v}')")
        return v



class TroubleshootingAnswerRequest(BaseModel):
    """User's answer to a troubleshooting question."""
    question_number: int = Field(gt=0, le=10)
    answer: str = Field(min_length=1, max_length=2000)


class TroubleshootingConfirmRequest(BaseModel):
    """Optional overrides when confirming and creating the issue."""
    # All fields from the draft can be overridden at confirm time
    title: str | None = None
    description: str | None = None
    priority_id: int | None = None
    severity_id: int | None = None
    status_id: int | None = None
    category_id: int | None = None
    module_id: int | None = None
    assigned_to: int | None = None
    environment: str | None = None
    browser: str | None = None
    operating_system: str | None = None
    sprint_id: int | None = None


# ── Response Schemas ──

class QuestionOptionResponse(BaseModel):
    id: str
    label: str


class CandidateRootCauseResponse(BaseModel):
    cause: str
    confidence: float


class TroubleshootingQuestionResponse(BaseModel):
    """A single question from the AI."""
    session_id: str
    status: str  # "questioning"
    question_number: int
    question: str
    question_type: str
    options: list[QuestionOptionResponse] | None = None
    candidate_root_causes: list[CandidateRootCauseResponse] = []


class TroubleshootingConfirmedResponse(BaseModel):
    """Root cause confirmed by the AI."""
    session_id: str
    status: str  # "confirmed"
    question_number: int
    root_cause: str
    confidence: float
    evidence: list[str] = []
    recommended_fix: str
    next_diagnostic_step: str | None = None


class TroubleshootingInsufficientResponse(BaseModel):
    """Insufficient evidence after max questions."""
    session_id: str
    status: str  # "insufficient_evidence"
    question_number: int
    root_cause: str
    confidence: float
    evidence: list[str] = []
    recommended_fix: str
    next_diagnostic_step: str | None = None


class TroubleshootingAnswerResponseItem(BaseModel):
    """Saved answer record."""
    question_number: int
    question_text: str
    question_type: str
    options: list[QuestionOptionResponse] | None = None
    selected_answer: str


class TroubleshootingSessionResponse(BaseModel):
    """Full session state for GET endpoint."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    status: str
    question_count: int
    current_question: dict | None = None
    root_cause: str | None = None
    confidence: float | None = None
    evidence_summary: list[str] | None = None
    recommended_fix: str | None = None
    next_diagnostic_step: str | None = None
    candidate_causes: list[CandidateRootCauseResponse] | None = None
    answers: list[TroubleshootingAnswerResponseItem] = []
    ai_model: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class TroubleshootingCreatedIssueResponse(BaseModel):
    """Response after confirming and creating the issue."""
    issue_id: int
    issue_key: str
    session_id: str
    root_cause: str | None = None
    confidence: float | None = None
    status: str  # "completed"
    similar_issues: list[dict] = []



class TroubleshootingErrorResponse(BaseModel):
    """Error response for AI failures — allows user to retry or skip."""
    session_id: str
    status: str  # "error"
    error: str
    can_retry: bool = True
    can_skip: bool = True

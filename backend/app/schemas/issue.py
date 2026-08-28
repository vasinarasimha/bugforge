from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

VALID_ISSUE_TYPES = {"Defect", "Task", "Feature"}

class IssueStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool

class IssuePriorityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool

class IssueSeverityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool

class IssueCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool

class IssueModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool

class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    issue_type: str = "Defect"
    project_id: int = Field(gt=0)
    priority_id: int = Field(gt=0)
    severity_id: int = Field(gt=0)
    status_id: int = Field(gt=0)
    category_id: int | None = Field(default=None, gt=0)
    module_id: int | None = Field(default=None, gt=0)
    assigned_to: int | None = Field(default=None, gt=0)
    environment: str | None = None
    browser: str | None = None
    operating_system: str | None = None
    reproduction_steps: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    root_cause: str | None = None
    resolution: str | None = None
    attachment_path: str | None = None
    sprint_id: int | None = None

    def model_post_init(self, __context):
        if self.issue_type not in VALID_ISSUE_TYPES:
            raise ValueError(f"issue_type must be one of {VALID_ISSUE_TYPES}")

class IssueUpdate(IssueCreate):
    ...

class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    issue_key: str
    title: str
    description: str
    issue_type: str
    status_id: int
    status_name: str
    priority_id: int
    priority_name: str
    severity_id: int
    severity_name: str
    category_id: int | None = None
    category_name: str | None = None
    module_id: int | None = None
    module_name: str | None = None
    environment: str | None
    browser: str | None
    operating_system: str | None
    reproduction_steps: str | None
    expected_behavior: str | None
    actual_behavior: str | None
    root_cause: str | None = None
    resolution: str | None = None
    attachment_path: str | None
    sprint_id: int | None
    sprint_name: str | None
    project_id: int
    project_name: str
    reporter_id: int
    reporter_name: str
    assigned_to: int | None
    assignee: str | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

class IssueCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)

class IssueCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    issue_id: int
    user_id: int
    user_name: str
    content: str
    created_at: datetime
    updated_at: datetime | None = None

class IssueHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    issue_id: int
    user_id: int | None
    user_name: str | None
    field_name: str
    old_value: str | None
    new_value: str | None
    created_at: datetime


# ── Semantic Similarity Schemas ──

class SimilarIssueResponse(BaseModel):
    """A similar or potentially duplicate issue found via semantic search."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    issue_key: str
    title: str
    description: str = ""
    status_id: int
    status_name: str
    severity_id: int
    severity_name: str
    priority_id: int
    priority_name: str
    category_name: str | None = None
    module_name: str | None = None
    project_id: int
    project_name: str = ""
    similarity_score: float
    similarity_percent: float
    similarity_label: str  # "Potential Duplicate" or "Similar Defect"


class IssueCreateResponse(BaseModel):
    """Extended create response that includes the created issue and any similar issues found."""
    model_config = ConfigDict(from_attributes=True)
    issue: IssueResponse
    similar_issues: list[SimilarIssueResponse] = []


class SemanticSearchRequest(BaseModel):
    """Request body for semantic search."""
    query: str = Field(min_length=3, max_length=1000)
    project_id: int | None = None
    limit: int | None = Field(default=None, ge=1, le=50)


class SemanticSearchResponse(BaseModel):
    """Single result item in semantic search."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    issue_key: str
    title: str
    description: str = ""
    status_id: int
    status_name: str
    severity_id: int
    severity_name: str
    priority_id: int
    priority_name: str
    category_name: str | None = None
    module_name: str | None = None
    project_id: int
    project_name: str = ""
    similarity_score: float
    similarity_percent: float
    similarity_label: str


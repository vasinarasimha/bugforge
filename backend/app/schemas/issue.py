from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

VALID_STATUSES = {"Open", "In Progress", "Resolved"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}


class IssueCreate(BaseModel):
    print('schemas/issue.py IssueCreate model initialized')
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    project_id: int = Field(gt=0)
    priority: str = "Medium"
    status: str = "Open"
    assigned_to: int | None = Field(default=None, gt=0)

    def model_post_init(self, __context):
        print('schemas/issue.py IssueCreate model initialized')
        if self.status not in VALID_STATUSES:
            print(f"schemas/issue.py Invalid status: {self.status}. Must be one of {VALID_STATUSES}")
            raise ValueError("status must be Open, In Progress, or Resolved")
        if self.priority not in VALID_PRIORITIES:
            print(f"schemas/issue.py Invalid priority: {self.priority}. Must be one of {VALID_PRIORITIES}")
            raise ValueError("priority must be Low, Medium, High, or Critical")


class IssueUpdate(IssueCreate):
    print('schemas/issue.py IssueUpdate model initialized')
    ...


class IssueResponse(BaseModel):
    print('schemas/issue.py IssueResponse model initialized')
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    status: str
    priority: str
    project_id: int
    project_name: str
    reporter_id: int
    reporter_name: str
    assigned_to: int | None
    created_at: datetime
    updated_at: datetime

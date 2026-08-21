from typing import Optional, List, Any
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

class SprintStatusResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class SprintBase(BaseModel):
    name: str
    goal: Optional[str] = None
    status_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    project_id: int

class SprintCreate(SprintBase):
    pass

class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    status_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class SprintResponse(SprintBase):
    id: int
    status_name: str
    project_name: str
    created_by: Optional[int] = None
    creator_name: Optional[str] = None
    created_at: datetime
    issue_count: int
    issues: List[Any] = []
    
    model_config = ConfigDict(from_attributes=True)

class SprintIssueAssign(BaseModel):
    issue_id: int

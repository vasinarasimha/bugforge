from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    key: str = Field(min_length=1, max_length=10)
    description: str | None = Field(default="", max_length=5000)
    repository_url: str | None = None
    status: str = "Active"
    client_name: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    budget: str | None = None
    tech_stack: str | None = None
    team_id: int | None = None
    project_manager_id: int | None = None
    team_leader_id: int | None = None


class ProjectUpdate(ProjectCreate):
    ...


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    key: str
    description: str
    repository_url: str | None
    status: str
    client_name: str | None
    start_date: datetime | None
    end_date: datetime | None
    budget: str | None
    tech_stack: str | None
    created_by: int
    creator_name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    issue_count: int = 0
    team_id: int | None = None
    team_name: str | None = None
    project_manager_id: int | None = None
    team_leader_id: int | None = None
    project_manager_name: str | None = None
    team_leader_name: str | None = None

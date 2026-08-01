from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    print('schemas/project.py ProjectCreate model initialized')
    project_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=5000)


class ProjectUpdate(ProjectCreate):
    print('schemas/project.py ProjectUpdate model initialized')
    ...


class ProjectResponse(BaseModel):
    print('schemas/project.py ProjectResponse model initialized')
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_name: str
    description: str
    created_by: int
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    issue_count: int = 0

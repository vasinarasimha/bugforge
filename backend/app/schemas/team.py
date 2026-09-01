from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class TeamMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str
    email: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    joined_at: datetime


class TeamLeaderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    job_title: Optional[str] = None


class ProjectManagerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    job_title: Optional[str] = None


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    team_leader_id: Optional[int] = None
    team_leader: Optional[TeamLeaderRead] = None
    project_manager_id: Optional[int] = None
    project_manager: Optional[ProjectManagerRead] = None
    is_active: bool = True
    member_count: int = 0
    members: List[TeamMemberRead] = []
    created_at: datetime
    updated_at: datetime


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    team_leader_id: Optional[int] = None
    project_manager_id: Optional[int] = None
    member_ids: List[int] = []
    is_active: bool = True


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    team_leader_id: Optional[int] = None
    project_manager_id: Optional[int] = None
    member_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


class AvailableEmployee(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    role: str
    current_team_id: Optional[int] = None
    current_team_name: Optional[str] = None
    is_assigned_as_leader: bool = False

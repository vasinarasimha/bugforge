from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    print('schemas/auth.py UserCreate model initialized')
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=list)


class UserLogin(BaseModel):
    print('schemas/auth.py UserLogin model initialized')
    email: EmailStr
    password: str = Field(min_length=1)


class RoleResponse(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    print('schemas/auth.py UserResponse model initialized')
    id: int
    full_name: str
    email: EmailStr
    roles: list[RoleResponse] = Field(default_factory=list)
    role: Optional[str] = None  # Computed convenience field: first role name
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    def set_primary_role(self) -> 'UserResponse':
        if self.roles and self.role is None:
            self.role = self.roles[0].name
        return self


class Token(BaseModel):
    print('schemas/auth.py Token model initialized')
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


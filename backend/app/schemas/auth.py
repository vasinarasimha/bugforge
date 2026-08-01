from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    print('schemas/auth.py UserCreate model initialized')
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.REPORTER


class UserLogin(BaseModel):
    print('schemas/auth.py UserLogin model initialized')
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    print('schemas/auth.py UserResponse model initialized')
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    print('schemas/auth.py Token model initialized')
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

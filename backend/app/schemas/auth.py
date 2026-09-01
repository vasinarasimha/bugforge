import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


VALID_ROLES = ["Admin", "Developer", "QA", "Reporter", "Project Manager", "Team Leader"]


class RoleResponse(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool = True
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    mobile_country_code: Optional[str] = None
    mobile_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    roles: list[RoleResponse] = Field(default_factory=list)
    role: Optional[str] = None  # Computed convenience field: first role name
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    def set_primary_role(self) -> 'UserResponse':
        if self.roles and self.role is None:
            self.role = self.roles[0].name
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Optional[str] = "Developer"
    roles: list[str] = Field(default_factory=list)
    job_title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    mobile_country_code: Optional[str] = Field(None, max_length=10)
    mobile_number: Optional[str] = Field(None, max_length=20)
    address_line_1: Optional[str] = Field(None, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    state_code: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=10)

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in VALID_ROLES:
            raise ValueError(f"Invalid role '{v}'. Allowed roles: {', '.join(VALID_ROLES)}")
        return v

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = re.sub(r'[\s\-()]', '', v)
            if not re.match(r'^\d{6,15}$', clean):
                raise ValueError("Invalid phone number. Must contain 6 to 15 digits.")
            return clean
        return v

    @field_validator('mobile_country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if not re.match(r'^\+?[0-9]{1,5}$', v.strip()):
                raise ValueError("Invalid country dialing code format (e.g. +91, +1).")
            return v.strip() if v.startswith('+') else f"+{v.strip()}"
        return v


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    role: Optional[str] = None
    roles: Optional[list[str]] = None
    is_active: Optional[bool] = None
    job_title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    mobile_country_code: Optional[str] = Field(None, max_length=10)
    mobile_number: Optional[str] = Field(None, max_length=20)
    address_line_1: Optional[str] = Field(None, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    state_code: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=10)

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in VALID_ROLES:
            raise ValueError(f"Invalid role '{v}'. Allowed roles: {', '.join(VALID_ROLES)}")
        return v

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = re.sub(r'[\s\-()]', '', v)
            if not re.match(r'^\d{6,15}$', clean):
                raise ValueError("Invalid phone number. Must contain 6 to 15 digits.")
            return clean
        return v

    @field_validator('mobile_country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if not re.match(r'^\+?[0-9]{1,5}$', v.strip()):
                raise ValueError("Invalid country dialing code format (e.g. +91, +1).")
            return v.strip() if v.startswith('+') else f"+{v.strip()}"
        return v


class SelfProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    job_title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    mobile_country_code: Optional[str] = Field(None, max_length=10)
    mobile_number: Optional[str] = Field(None, max_length=20)
    address_line_1: Optional[str] = Field(None, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    state_code: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=10)

    # Extra fields forbidden to prevent tampering with email, role, is_active, password
    model_config = ConfigDict(extra='forbid')

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = re.sub(r'[\s\-()]', '', v)
            if not re.match(r'^\d{6,15}$', clean):
                raise ValueError("Invalid phone number. Must contain 6 to 15 digits.")
            return clean
        return v

    @field_validator('mobile_country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if not re.match(r'^\+?[0-9]{1,5}$', v.strip()):
                raise ValueError("Invalid country dialing code format (e.g. +91, +1).")
            return v.strip() if v.startswith('+') else f"+{v.strip()}"
        return v


# Kept for backward compatibility if imported elsewhere
UserCreate = AdminUserCreate

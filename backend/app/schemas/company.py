from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Company Schemas ──

class CompanyBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=255)
    address_line_1: Optional[str] = Field(default=None, max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)


class InitialAdminCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    job_title: Optional[str] = "Company Administrator"
    department: Optional[str] = "Administration"
    mobile_number: Optional[str] = None


class CompanyCreateWithAdmin(CompanyBase):
    """Atomic creation of Company + Settings + Initial Company Admin."""
    admin: InitialAdminCreate


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=255)
    address_line_1: Optional[str] = Field(default=None, max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)
    logo_url: Optional[str] = None


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    logo_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Aggregated platform counts (calculated)
    projects_count: int = 0
    issues_count: int = 0
    admins_count: int = 0
    users_count: int = 0


class CompanyDetailResponse(CompanyResponse):
    open_issues_count: int = 0
    resolved_issues_count: int = 0
    critical_issues_count: int = 0
    active_projects_count: int = 0


# ── Company Settings Schemas ──

class CompanySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    settings: dict[str, Any]
    updated_at: datetime


class CompanySettingsUpdate(BaseModel):
    settings: dict[str, Any]


# ── Customization Request Schemas ──

class CustomizationRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(default="Workflow", max_length=50)
    requested_behavior: str = Field(min_length=10, max_length=5000)


class CustomizationRequestReview(BaseModel):
    status: str = Field(pattern=r"^(Pending|Under Review|Approved|Rejected|Implemented|Cancelled)$")
    super_admin_notes: Optional[str] = None


class CustomizationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    company_name: Optional[str] = None
    requester_id: int
    requester_name: Optional[str] = None
    title: str
    description: str
    category: str
    requested_behavior: str
    status: str
    super_admin_notes: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ── Audit Log Schema ──

class CompanyAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    created_at: datetime


# ── Super Admin Dashboard & Analytics Schemas (Company-Level Only) ──

class CompanyActivityItem(BaseModel):
    company_id: int
    company_name: str
    is_active: bool
    projects_count: int
    open_issues: int
    resolved_issues: int
    critical_issues: int
    total_issues: int
    created_at: datetime


class PlatformDashboardResponse(BaseModel):
    total_companies: int
    active_companies: int
    inactive_companies: int
    new_companies_last_7_days: int
    new_companies_last_30_days: int
    total_platform_projects: int
    total_platform_issues: int
    companies_activity: list[CompanyActivityItem]


class CompanyGrowthPoint(BaseModel):
    date: str
    companies_count: int


class CompanyDefectMetric(BaseModel):
    company_id: int
    company_name: str
    defects_created: int
    defects_resolved: int
    open_defects: int
    critical_defects: int
    avg_resolution_hours: float


class PlatformAnalyticsResponse(BaseModel):
    total_companies: int
    active_companies: int
    inactive_companies: int
    growth_trend: list[CompanyGrowthPoint]
    company_metrics: list[CompanyDefectMetric]

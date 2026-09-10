"""
Super Admin API Routes.

Exclusively accessible to platform Super Administrators (UserRole.SUPER_ADMIN).
Provides platform-level company management, company-level platform dashboard & analytics,
and customization request reviews.
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies.auth import require_role
from app.core.database import get_db
from app.models.company_audit_log import CompanyAuditLog
from app.models.user import User, UserRole
from app.schemas.company import (
    CompanyCreateWithAdmin,
    CompanyUpdate,
    CompanyResponse,
    CompanyDetailResponse,
    PlatformDashboardResponse,
    PlatformAnalyticsResponse,
    CustomizationRequestReview,
    CustomizationRequestResponse,
    CompanyAuditLogResponse,
)
from app.services.super_admin_service import SuperAdminService

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])
service = SuperAdminService()


@router.get("/dashboard", response_model=PlatformDashboardResponse)
def get_platform_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
):
    """
    Super Admin platform dashboard. Strictly company-level summaries.
    No individual developer performance or rankings.
    """
    return service.get_platform_dashboard(db)


@router.get("/analytics", response_model=PlatformAnalyticsResponse)
def get_platform_analytics(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
    company_id: Optional[int] = Query(default=None, description="Optional: filter by company ID"),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days"),
):
    """
    Super Admin platform analytics.
    Company growth and company-wise defect volume and resolution metrics.
    """
    return service.get_platform_analytics(db, company_id=company_id, days=days)


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    """List all tenant companies on the platform with company-level aggregates."""
    return service.list_companies(db, search=search, is_active=is_active)


@router.post("/companies", status_code=status.HTTP_201_CREATED)
def create_company_with_admin(
    data: CompanyCreateWithAdmin,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
):
    """
    Create a new company, default settings, default statuses, and its initial Company Admin atomically.
    """
    return service.create_company_with_admin(db, data, current_user)


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
def get_company_detail(
    company_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
):
    """Get company profile and company-level aggregate metrics."""
    return service.get_company_detail(db, company_id)


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
):
    """Update company profile information."""
    return service.update_company(db, company_id, data, current_user)


@router.patch("/companies/{company_id}/status", response_model=CompanyResponse)
def toggle_company_status(
    company_id: int,
    is_active: bool,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
):
    """Soft activate or deactivate a company without deleting historical data."""
    return service.set_company_active_status(db, company_id, is_active, current_user)


@router.get("/companies/{company_id}/audit-logs", response_model=list[CompanyAuditLogResponse])
def get_company_audit_logs(
    company_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
    limit: int = Query(default=50, ge=1, le=200),
):
    """View audit trail of changes for a specific company."""
    logs = db.query(CompanyAuditLog).options(
        joinedload(CompanyAuditLog.user)
    ).filter(
        CompanyAuditLog.company_id == company_id
    ).order_by(CompanyAuditLog.created_at.desc()).limit(limit).all()

    return [
        CompanyAuditLogResponse(
            id=l.id,
            company_id=l.company_id,
            user_id=l.user_id,
            user_name=l.user.full_name if l.user else None,
            action=l.action,
            entity_type=l.entity_type,
            entity_id=l.entity_id,
            old_value=l.old_value,
            new_value=l.new_value,
            created_at=l.created_at,
        )
        for l in logs
    ]


# ── Customization Requests ──

@router.get("/customization-requests", response_model=list[CustomizationRequestResponse])
def list_customization_requests(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
    status: Optional[str] = Query(default=None),
):
    """View all customization requests submitted by Company Admins across the platform."""
    return service.list_customization_requests(db, status_filter=status)


@router.patch("/customization-requests/{request_id}", response_model=CustomizationRequestResponse)
def review_customization_request(
    request_id: int,
    review_data: CustomizationRequestReview,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.SUPER_ADMIN]))],
):
    """Review and update the status of a customization request with Super Admin notes."""
    return service.review_customization_request(db, request_id, review_data, current_user)

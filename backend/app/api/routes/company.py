"""
Company Admin API Routes.

Exclusively accessible to Company Administrators (UserRole.ADMIN).
All operations are strictly bounded to the authenticated admin's company_id.
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.company import (
    CompanyUpdate,
    CompanyResponse,
    CompanySettingsResponse,
    CompanySettingsUpdate,
    CustomizationRequestCreate,
    CustomizationRequestResponse,
    CompanyAuditLogResponse,
)
from app.schemas.issue import IssueStatusCreate, IssueStatusUpdate
from app.services.company_settings_service import CompanySettingsService

router = APIRouter(prefix="/company", tags=["Company Profile & Settings"])
service = CompanySettingsService()


def _ensure_company_id(user: User) -> int:
    if not user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is not assigned to any tenant company."
        )
    return user.company_id


# ── Company Profile ──

@router.get("/profile")
def get_company_profile(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Retrieve own company profile."""
    cid = _ensure_company_id(current_user)
    return service.get_company_profile(db, cid)


@router.patch("/profile")
def update_company_profile(
    data: CompanyUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Update allowed company profile details."""
    cid = _ensure_company_id(current_user)
    return service.update_company_profile(db, cid, data, current_user)


# ── Company Settings (Structured & Extensible) ──

@router.get("/settings", response_model=CompanySettingsResponse)
def get_company_settings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Retrieve extensible company configuration (workflow rules, feature toggles, notifications)."""
    cid = _ensure_company_id(current_user)
    return service.get_settings(db, cid)


@router.put("/settings", response_model=CompanySettingsResponse)
def update_company_settings(
    data: CompanySettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Update company settings and record change in audit log."""
    cid = _ensure_company_id(current_user)
    return service.update_settings(db, cid, data.settings, current_user)


# ── Dynamic Issue Statuses ──

@router.get("/statuses")
def list_company_statuses(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """List all workflow issue statuses configured for this company, with existing issue counts."""
    cid = _ensure_company_id(current_user)
    return service.list_statuses(db, cid)


@router.post("/statuses", status_code=status.HTTP_201_CREATED)
def create_company_status(
    data: IssueStatusCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Add a new company-specific issue status."""
    cid = _ensure_company_id(current_user)
    return service.create_status(db, cid, data, current_user)


@router.patch("/statuses/{status_id}")
def update_company_status(
    status_id: int,
    data: IssueStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Update status configuration (name, color, order, active/inactive)."""
    cid = _ensure_company_id(current_user)
    return service.update_status(db, cid, status_id, data, current_user)


@router.delete("/statuses/{status_id}")
def delete_or_deactivate_status(
    status_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """
    Safely delete or deactivate a status.
    If issues already use the status, it is deactivated with a clear dependency warning.
    """
    cid = _ensure_company_id(current_user)
    return service.delete_or_deactivate_status(db, cid, status_id, current_user)


# ── Customization Requests ──

@router.get("/customization-requests", response_model=list[CustomizationRequestResponse])
def list_customization_requests(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """View all customization requests submitted by this company."""
    cid = _ensure_company_id(current_user)
    return service.list_customization_requests(db, cid)


@router.post("/customization-requests", response_model=CustomizationRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_customization_request(
    data: CustomizationRequestCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Submit a new feature/customization request to platform Super Admin."""
    cid = _ensure_company_id(current_user)
    return service.submit_customization_request(db, cid, data, current_user)


# ── Audit Trail ──

@router.get("/audit-logs", response_model=list[CompanyAuditLogResponse])
def list_company_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
    limit: int = Query(default=50, ge=1, le=200),
):
    """View audit history of configuration changes for this company."""
    cid = _ensure_company_id(current_user)
    return service.list_audit_logs(db, cid, limit=limit)

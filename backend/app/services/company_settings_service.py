"""
Company Settings & Customization Service.

Enforces strict company-scoped administration for Company Admins:
- Company Profile editing (restricted to own company)
- Configurable settings stored in CompanySettings
- Dynamic issue statuses (Add, edit, reorder, active/inactive toggle with dependency warning)
- Customization request submission
- Audit logging of all configuration changes
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.company import Company, CompanySettings
from app.models.company_audit_log import CompanyAuditLog
from app.models.customization_request import CustomizationRequest
from app.models.issue import Issue, IssueStatus
from app.models.user import User
from app.schemas.company import (
    CompanyUpdate,
    CompanyResponse,
    CompanySettingsResponse,
    CompanySettingsUpdate,
    CustomizationRequestCreate,
    CustomizationRequestResponse,
    CompanyAuditLogResponse,
)
from app.schemas.issue import IssueStatusCreate, IssueStatusUpdate, IssueStatusResponse

logger = logging.getLogger(__name__)


class CompanySettingsService:

    def get_company_profile(self, db: Session, company_id: int) -> dict[str, Any]:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        return {
            "id": company.id,
            "name": company.name,
            "legal_name": company.legal_name,
            "email": company.email,
            "phone": company.phone,
            "website": company.website,
            "address_line_1": company.address_line_1,
            "address_line_2": company.address_line_2,
            "city": company.city,
            "state": company.state,
            "country": company.country,
            "logo_url": company.logo_url,
            "timezone": company.timezone,
            "is_active": company.is_active,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
        }

    def update_company_profile(
        self, db: Session, company_id: int, data: CompanyUpdate, user: User
    ) -> dict[str, Any]:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        old_values = {
            "legal_name": company.legal_name,
            "email": company.email,
            "phone": company.phone,
            "website": company.website,
            "city": company.city,
            "state": company.state,
            "country": company.country,
        }

        update_data = data.model_dump(exclude_unset=True)
        # Note: Company Admin can update profile details, but not arbitrary deactivation or name hijacking
        for k, v in update_data.items():
            if k not in ["id", "is_active", "created_at"]:
                setattr(company, k, v.strip() if isinstance(v, str) else v)

        db.add(CompanyAuditLog(
            company_id=company_id,
            user_id=user.id,
            action="PROFILE_UPDATED",
            entity_type="COMPANY",
            entity_id=company_id,
            old_value=old_values,
            new_value=update_data,
        ))

        db.commit()
        db.refresh(company)
        return self.get_company_profile(db, company_id)

    # ── Company Settings ──

    def get_settings(self, db: Session, company_id: int) -> dict[str, Any]:
        cs = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
        if not cs:
            # Initialize if missing
            default_settings = {
                "workflow": {
                    "default_status": "Open",
                    "resolved_status": "Resolved",
                    "closed_status": "Closed",
                    "require_resolution_notes": True,
                    "require_root_cause": True,
                },
                "features": {
                    "ai_root_cause_analysis": True,
                    "semantic_search": True,
                    "duplicate_detection": True,
                    "sprint_management": True,
                },
                "notifications": {
                    "email_on_assignment": True,
                    "email_on_status_change": True,
                }
            }
            cs = CompanySettings(company_id=company_id, settings=default_settings)
            db.add(cs)
            db.commit()
            db.refresh(cs)

        return {
            "id": cs.id,
            "company_id": cs.company_id,
            "settings": cs.settings or {},
            "updated_at": cs.updated_at,
        }

    def update_settings(
        self, db: Session, company_id: int, new_settings: dict[str, Any], user: User
    ) -> dict[str, Any]:
        cs = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
        if not cs:
            cs = CompanySettings(company_id=company_id, settings={})
            db.add(cs)
            db.flush()

        old_settings = dict(cs.settings or {})
        # Merge settings dictionary
        merged = {**old_settings, **new_settings}
        cs.settings = merged

        db.add(CompanyAuditLog(
            company_id=company_id,
            user_id=user.id,
            action="SETTINGS_UPDATED",
            entity_type="COMPANY_SETTINGS",
            entity_id=cs.id,
            old_value=old_settings,
            new_value=merged,
        ))

        db.commit()
        db.refresh(cs)
        return {
            "id": cs.id,
            "company_id": cs.company_id,
            "settings": cs.settings,
            "updated_at": cs.updated_at,
        }

    # ── Dynamic Status Management ──

    def list_statuses(self, db: Session, company_id: int) -> list[dict[str, Any]]:
        """List statuses configured for this company, with associated issue count."""
        company_statuses = db.query(IssueStatus).filter(
            IssueStatus.company_id == company_id
        ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()

        statuses = company_statuses if company_statuses else db.query(IssueStatus).filter(
            IssueStatus.company_id == None
        ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()

        results = []
        for s in statuses:
            # Count issues in this company using this status
            issue_count = db.query(func.count(Issue.id)).filter(
                Issue.company_id == company_id,
                Issue.status_id == s.id,
                Issue.is_deleted == False
            ).scalar() or 0

            results.append({
                "id": s.id,
                "name": s.name,
                "category": s.category or "open",
                "color": s.color or "#6366f1",
                "order_index": s.order_index,
                "is_initial": s.is_initial,
                "is_final": s.is_final,
                "is_active": s.is_active,
                "company_id": s.company_id,
                "issue_count": issue_count,
            })
        return results

    def create_status(
        self, db: Session, company_id: int, data: IssueStatusCreate, user: User
    ) -> dict[str, Any]:
        """Add a company-specific issue status."""
        name_clean = data.name.strip()

        # Check duplicate name within company
        existing = db.query(IssueStatus).filter(
            IssueStatus.company_id == company_id,
            func.lower(IssueStatus.name) == name_clean.lower()
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A status named '{name_clean}' already exists for your company."
            )

        # If marking as initial, clear is_initial on others
        if data.is_initial:
            db.query(IssueStatus).filter(
                IssueStatus.company_id == company_id,
                IssueStatus.is_initial == True
            ).update({"is_initial": False})

        status_obj = IssueStatus(
            name=name_clean,
            category=data.category,
            color=data.color or "#6366f1",
            order_index=data.order_index,
            is_initial=data.is_initial,
            is_final=data.is_final,
            is_active=True,
            company_id=company_id,
        )
        db.add(status_obj)
        db.flush()

        db.add(CompanyAuditLog(
            company_id=company_id,
            user_id=user.id,
            action="STATUS_CREATED",
            entity_type="ISSUE_STATUS",
            entity_id=status_obj.id,
            new_value={"name": status_obj.name, "category": status_obj.category, "color": status_obj.color},
        ))

        db.commit()
        db.refresh(status_obj)

        return {
            "id": status_obj.id,
            "name": status_obj.name,
            "category": status_obj.category,
            "color": status_obj.color,
            "order_index": status_obj.order_index,
            "is_initial": status_obj.is_initial,
            "is_final": status_obj.is_final,
            "is_active": status_obj.is_active,
            "company_id": status_obj.company_id,
            "issue_count": 0,
        }

    def update_status(
        self, db: Session, company_id: int, status_id: int, data: IssueStatusUpdate, user: User
    ) -> dict[str, Any]:
        status_obj = db.query(IssueStatus).filter(
            IssueStatus.id == status_id,
            IssueStatus.company_id == company_id
        ).first()
        if not status_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")

        old_val = {
            "name": status_obj.name,
            "is_active": status_obj.is_active,
            "order_index": status_obj.order_index,
            "category": status_obj.category,
        }

        update_dict = data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"]:
            new_name = update_dict["name"].strip()
            if new_name.lower() != status_obj.name.lower():
                dup = db.query(IssueStatus).filter(
                    IssueStatus.company_id == company_id,
                    func.lower(IssueStatus.name) == new_name.lower(),
                    IssueStatus.id != status_id
                ).first()
                if dup:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Status name '{new_name}' already exists."
                    )
            status_obj.name = new_name

        if "is_initial" in update_dict and update_dict["is_initial"] is True:
            # Unmark other initial statuses
            db.query(IssueStatus).filter(
                IssueStatus.company_id == company_id,
                IssueStatus.id != status_id,
                IssueStatus.is_initial == True
            ).update({"is_initial": False})
            status_obj.is_initial = True

        for k in ["category", "color", "order_index", "is_final", "is_active"]:
            if k in update_dict and update_dict[k] is not None:
                setattr(status_obj, k, update_dict[k])

        db.add(CompanyAuditLog(
            company_id=company_id,
            user_id=user.id,
            action="STATUS_UPDATED",
            entity_type="ISSUE_STATUS",
            entity_id=status_obj.id,
            old_value=old_val,
            new_value=update_dict,
        ))

        db.commit()
        db.refresh(status_obj)

        issue_count = db.query(func.count(Issue.id)).filter(
            Issue.company_id == company_id,
            Issue.status_id == status_obj.id,
            Issue.is_deleted == False
        ).scalar() or 0

        return {
            "id": status_obj.id,
            "name": status_obj.name,
            "category": status_obj.category,
            "color": status_obj.color,
            "order_index": status_obj.order_index,
            "is_initial": status_obj.is_initial,
            "is_final": status_obj.is_final,
            "is_active": status_obj.is_active,
            "company_id": status_obj.company_id,
            "issue_count": issue_count,
        }

    def delete_or_deactivate_status(
        self, db: Session, company_id: int, status_id: int, user: User
    ) -> dict[str, Any]:
        """
        Dependency-aware status removal.
        If existing issues reference it:
        - Strictly forbids physical deletion
        - Deactivates status for new issues while preserving history
        - Returns explicit dependency warning explaining issue count
        If no issues use it:
        - Deletes cleanly.
        """
        status_obj = db.query(IssueStatus).filter(
            IssueStatus.id == status_id,
            IssueStatus.company_id == company_id
        ).first()
        if not status_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")

        # Check total active statuses - prevent 0 active statuses
        active_count = db.query(func.count(IssueStatus.id)).filter(
            IssueStatus.company_id == company_id,
            IssueStatus.is_active == True
        ).scalar() or 0
        if active_count <= 1 and status_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete or deactivate the only remaining active status in your company."
            )

        # Count issues using this status
        issue_count = db.query(func.count(Issue.id)).filter(
            Issue.company_id == company_id,
            Issue.status_id == status_id,
            Issue.is_deleted == False
        ).scalar() or 0

        if issue_count > 0:
            # Cannot physically delete — deactivate with clear dependency explanation
            status_obj.is_active = False
            db.add(CompanyAuditLog(
                company_id=company_id,
                user_id=user.id,
                action="STATUS_DEACTIVATED_DUE_TO_DEPENDENCIES",
                entity_type="ISSUE_STATUS",
                entity_id=status_obj.id,
                new_value={"is_active": False, "issue_count": issue_count},
            ))
            db.commit()
            return {
                "action": "deactivated",
                "status_id": status_id,
                "is_active": False,
                "issue_count": issue_count,
                "message": (
                    f"{issue_count} existing issue(s) currently use status '{status_obj.name}'. "
                    f"The status has been deactivated for new issues, but historical records will retain it."
                ),
            }
        else:
            # Safely delete
            db.add(CompanyAuditLog(
                company_id=company_id,
                user_id=user.id,
                action="STATUS_DELETED",
                entity_type="ISSUE_STATUS",
                entity_id=status_obj.id,
                old_value={"name": status_obj.name},
            ))
            db.delete(status_obj)
            db.commit()
            return {
                "action": "deleted",
                "status_id": status_id,
                "message": f"Status '{status_obj.name}' was completely removed since no issues reference it.",
            }

    # ── Customization Requests (Company Side) ──

    def submit_customization_request(
        self, db: Session, company_id: int, data: CustomizationRequestCreate, user: User
    ) -> CustomizationRequestResponse:
        req = CustomizationRequest(
            company_id=company_id,
            requester_id=user.id,
            title=data.title.strip(),
            description=data.description.strip(),
            category=data.category.strip(),
            requested_behavior=data.requested_behavior.strip(),
            status="Pending",
        )
        db.add(req)
        db.flush()

        db.add(CompanyAuditLog(
            company_id=company_id,
            user_id=user.id,
            action="CUSTOMIZATION_REQUEST_SUBMITTED",
            entity_type="CUSTOMIZATION_REQUEST",
            entity_id=req.id,
            new_value={"title": req.title, "category": req.category},
        ))

        # Integrate with BugForge internal issue workflow as Issue Type = 'Feature'
        from app.services.issue_service import IssueService
        feature_desc = f"{data.description.strip()}\n\nRequested Behavior:\n{data.requested_behavior.strip()}"
        try:
            IssueService().submit_feature_request(
                db=db,
                title=data.title.strip(),
                description=feature_desc,
                user=user,
            )
        except Exception as e:
            logger.error(f"Failed to create Feature issue from customization request: {e}")

        db.commit()
        db.refresh(req)

        return CustomizationRequestResponse(
            id=req.id,
            company_id=req.company_id,
            company_name=user.company_name or "Your Company",
            requester_id=req.requester_id,
            requester_name=user.full_name,
            title=req.title,
            description=req.description,
            category=req.category,
            requested_behavior=req.requested_behavior,
            status=req.status,
            super_admin_notes=req.super_admin_notes,
            reviewed_by_id=req.reviewed_by_id,
            reviewer_name=None,
            reviewed_at=req.reviewed_at,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )

    def list_customization_requests(
        self, db: Session, company_id: int
    ) -> list[CustomizationRequestResponse]:
        requests = db.query(CustomizationRequest).options(
            joinedload(CustomizationRequest.requester),
            joinedload(CustomizationRequest.reviewer)
        ).filter(
            CustomizationRequest.company_id == company_id
        ).order_by(CustomizationRequest.created_at.desc()).all()

        return [
            CustomizationRequestResponse(
                id=r.id,
                company_id=r.company_id,
                company_name=r.company.name if r.company else "Your Company",
                requester_id=r.requester_id,
                requester_name=r.requester.full_name if r.requester else "Unknown",
                title=r.title,
                description=r.description,
                category=r.category,
                requested_behavior=r.requested_behavior,
                status=r.status,
                super_admin_notes=r.super_admin_notes,
                reviewed_by_id=r.reviewed_by_id,
                reviewer_name=r.reviewer.full_name if r.reviewer else None,
                reviewed_at=r.reviewed_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in requests
        ]

    # ── Audit Trail ──

    def list_audit_logs(
        self, db: Session, company_id: int, limit: int = 50
    ) -> list[CompanyAuditLogResponse]:
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


company_settings_service = CompanySettingsService()


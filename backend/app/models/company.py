"""
Company / Organization models for multi-tenant architecture.

Every company-owned entity (users, projects, teams, issues, etc.)
must reference a Company to enforce strict tenant isolation.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, JSON, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.team import Team
    from app.models.issue import IssueStatus
    from app.models.customization_request import CustomizationRequest
    from app.models.company_audit_log import CompanyAuditLog


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="company")
    projects: Mapped[list["Project"]] = relationship(back_populates="company")
    teams: Mapped[list["Team"]] = relationship(back_populates="company")
    settings: Mapped["CompanySettings | None"] = relationship(
        back_populates="company", uselist=False, cascade="all, delete-orphan"
    )
    statuses: Mapped[list["IssueStatus"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    customization_requests: Mapped[list["CustomizationRequest"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["CompanyAuditLog"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanySettings(Base):
    """
    Scalable company-level configuration.

    Uses a JSON column so new settings can be added without schema changes.
    Individual settings are accessed/updated through the service layer
    which validates allowed keys and value types.
    """
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True
    )
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="settings")

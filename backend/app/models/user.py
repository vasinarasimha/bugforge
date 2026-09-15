import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.project import Project
    from app.models.collaboration import ActivityLog, Attachment, Comment
    from app.models.company import Company
    from app.models.notification import Notification

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "Super Admin"
    ADMIN = "Admin"
    DEVELOPER = "Developer"
    QA = "QA"
    REPORTER = "Reporter"
    PROJECT_MANAGER = "Project Manager"
    TEAM_LEADER = "Team Leader"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mobile_country_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mobile_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_system_user: Mapped[bool] = mapped_column(default=False, nullable=False)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped["Company | None"] = relationship(back_populates="users")
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")
    projects: Mapped[list["Project"]] = relationship(back_populates="creator", foreign_keys="Project.created_by")
    reported_issues: Mapped[list["Issue"]] = relationship(foreign_keys="Issue.reporter_id", back_populates="reporter")
    assigned_issues: Mapped[list["Issue"]] = relationship(foreign_keys="Issue.assigned_to", back_populates="assignee")
    assigned_qa_issues: Mapped[list["Issue"]] = relationship(foreign_keys="Issue.assigned_qa_id", back_populates="assigned_qa")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="recipient",
        foreign_keys="Notification.recipient_id",
        cascade="all, delete-orphan",
    )

    @property
    def company_name(self) -> str | None:
        return self.company.name if self.company else None



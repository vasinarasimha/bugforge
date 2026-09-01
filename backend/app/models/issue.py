from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.label import IssueLabel
    from app.models.sprint import Sprint
    from app.models.attachment import IssueAttachment
    from app.models.troubleshooting import TroubleshootingSession


class IssueStatus(Base):
    __tablename__ = "issue_statuses"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

class IssuePriority(Base):
    __tablename__ = "issue_priorities"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

class IssueSeverity(Base):
    __tablename__ = "issue_severities"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

class IssueCategory(Base):
    __tablename__ = "issue_categories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

class IssueModule(Base):
    __tablename__ = "issue_modules"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_key: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(32), nullable=False, default="Defect")
    status_id: Mapped[int] = mapped_column(ForeignKey("issue_statuses.id"), nullable=False)
    priority_id: Mapped[int] = mapped_column(ForeignKey("issue_priorities.id"), nullable=False)
    severity_id: Mapped[int] = mapped_column(ForeignKey("issue_severities.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("issue_categories.id"), nullable=True)
    module_id: Mapped[int | None] = mapped_column(ForeignKey("issue_modules.id"), nullable=True)
    
    environment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reproduction_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    embedding_vector = mapped_column(Vector(384), nullable=True)

    # AI Root-Cause Analysis session (populated when created via troubleshooting flow)
    ai_root_cause_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("troubleshooting_sessions.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="issues")
    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id], back_populates="reported_issues")
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assigned_to], back_populates="assigned_issues")
    status: Mapped["IssueStatus"] = relationship()
    priority: Mapped["IssuePriority"] = relationship()
    severity: Mapped["IssueSeverity"] = relationship()
    category: Mapped["IssueCategory | None"] = relationship()
    module: Mapped["IssueModule | None"] = relationship()
    labels: Mapped[list["IssueLabel"]] = relationship(secondary="issue_label_mapping", back_populates="issues")
    sprint: Mapped["Sprint | None"] = relationship(back_populates="issues")
    attachments: Mapped[list["IssueAttachment"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    ai_root_cause_session: Mapped["TroubleshootingSession | None"] = relationship()

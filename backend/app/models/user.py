import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.project import Project


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    DEVELOPER = "Developer"
    QA = "QA"
    REPORTER = "Reporter"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_type: [role.value for role in enum_type],
        ),
        nullable=False,
        default=UserRole.REPORTER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="creator")
    reported_issues: Mapped[list["Issue"]] = relationship(foreign_keys="Issue.reporter_id", back_populates="reporter")
    assigned_issues: Mapped[list["Issue"]] = relationship(foreign_keys="Issue.assigned_to", back_populates="assignee")


for role in UserRole:
    print(f"models/user.py UserRole: {role.value}")
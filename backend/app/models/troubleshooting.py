from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class TroubleshootingSession(Base):
    """
    Stores an AI-driven root-cause analysis session.
    Each session is tied to one defect creation attempt and one user.
    State machine: started → questioning → confirmed/insufficient_evidence → completed | cancelled
    """
    __tablename__ = "troubleshooting_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="started")

    # Snapshot of the defect draft at session start
    defect_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Question tracking
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Root-cause results
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_summary: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommended_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_diagnostic_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_causes: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Metadata
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship()
    answers: Mapped[list["TroubleshootingAnswer"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="TroubleshootingAnswer.question_number"
    )


class TroubleshootingAnswer(Base):
    """
    Stores an individual question-answer pair within a troubleshooting session.
    """
    __tablename__ = "troubleshooting_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("troubleshooting_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False, default="multiple_choice")
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session: Mapped["TroubleshootingSession"] = relationship(back_populates="answers")

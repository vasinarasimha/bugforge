from sqlalchemy import ForeignKey, String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.core.database import Base
from app.models.user import User

class IssueAttachment(Base):
    __tablename__ = 'issue_attachments'
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey('issues.id'))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    
    issue = relationship('Issue', back_populates='attachments')
    uploader = relationship('User')

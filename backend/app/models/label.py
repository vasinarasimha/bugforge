from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

issue_label_mapping = Table('issue_label_mapping', Base.metadata, Column('issue_id', ForeignKey('issues.id', ondelete='CASCADE'), primary_key=True), Column('label_id', ForeignKey('issue_labels.id', ondelete='CASCADE'), primary_key=True))

class IssueLabel(Base):
    __tablename__ = 'issue_labels'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'))
    project = relationship('Project', back_populates='labels')
    issues = relationship('Issue', secondary=issue_label_mapping, back_populates='labels')

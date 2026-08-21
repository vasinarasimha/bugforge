from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.sprint import Sprint, SprintStatus
from app.models.issue import Issue
from app.schemas.sprint import SprintCreate, SprintUpdate


class SprintService:

    def list_statuses(self, db: Session):
        return db.query(SprintStatus).filter(SprintStatus.is_active == True).all()

    def list(self, db: Session, project_id: int | None = None):
        q = db.query(Sprint)
        if project_id:
            q = q.filter(Sprint.project_id == project_id)
        return q.order_by(Sprint.created_at.desc()).all()

    def get(self, db: Session, sprint_id: int):
        sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
        if not sprint:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Sprint not found")
        return sprint

    def create(self, db: Session, data: SprintCreate, user):
        # Validate status
        st = db.query(SprintStatus).filter(SprintStatus.id == data.status_id).first()
        if not st:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid sprint status")
        sprint = Sprint(
            name=data.name,
            goal=data.goal,
            status_id=data.status_id,
            start_date=data.start_date,
            end_date=data.end_date,
            project_id=data.project_id,
            created_by=user.id,
        )
        db.add(sprint)
        db.commit()
        db.refresh(sprint)
        return sprint

    def update(self, db: Session, sprint_id: int, data: SprintUpdate):
        sprint = self.get(db, sprint_id)
        if data.status_id is not None:
            st = db.query(SprintStatus).filter(SprintStatus.id == data.status_id).first()
            if not st:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid sprint status")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(sprint, field, value)
        db.commit()
        db.refresh(sprint)
        return sprint

    def delete(self, db: Session, sprint_id: int):
        sprint = self.get(db, sprint_id)
        # Unlink issues before deleting
        db.query(Issue).filter(Issue.sprint_id == sprint_id).update({"sprint_id": None})
        db.delete(sprint)
        db.commit()

    def assign_issue(self, db: Session, sprint_id: int, issue_id: int, user):
        sprint = self.get(db, sprint_id)
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")

        from app.models.history import IssueHistory
        old_sprint_id = issue.sprint_id
        if old_sprint_id != sprint_id:
            old_name = sprint.name if old_sprint_id else None
            if old_sprint_id:
                old_s = db.query(Sprint).filter(Sprint.id == old_sprint_id).first()
                old_name = old_s.name if old_s else str(old_sprint_id)
            history = IssueHistory(
                issue_id=issue.id,
                user_id=user.id,
                field_name="sprint_id",
                old_value=old_name,
                new_value=sprint.name,
            )
            db.add(history)
            issue.sprint_id = sprint_id
            db.commit()
        return issue

    def remove_issue(self, db: Session, sprint_id: int, issue_id: int, user):
        sprint = self.get(db, sprint_id)
        issue = db.query(Issue).filter(Issue.id == issue_id, Issue.sprint_id == sprint_id).first()
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not in this sprint")

        from app.models.history import IssueHistory
        history = IssueHistory(
            issue_id=issue.id,
            user_id=user.id,
            field_name="sprint_id",
            old_value=sprint.name,
            new_value=None,
        )
        db.add(history)
        issue.sprint_id = None
        db.commit()
        return issue

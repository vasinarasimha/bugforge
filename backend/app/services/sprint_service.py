from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_effective_company_id
from app.models.sprint import Sprint, SprintStatus
from app.models.issue import Issue
from app.schemas.sprint import SprintCreate, SprintUpdate


class SprintService:

    def list_statuses(self, db: Session):
        return db.query(SprintStatus).filter(SprintStatus.is_active == True).all()

    def list(self, db: Session, project_id: int | None = None, company_id: int | None = None):
        q = db.query(Sprint)
        if company_id is not None:
            from app.models.project import Project
            q = q.join(Project, Sprint.project_id == Project.id).filter(Project.company_id == company_id)
        if project_id:
            q = q.filter(Sprint.project_id == project_id)
        return q.order_by(Sprint.created_at.desc()).all()

    def get(self, db: Session, sprint_id: int, company_id: int | None = None):
        sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
        if not sprint:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Sprint not found")
        if company_id is not None and getattr(sprint, 'project', None) and getattr(sprint.project, 'company_id', None) != company_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized access to sprint belonging to another company")
        return sprint

    def create(self, db: Session, data: SprintCreate, user):
        from app.models.project import Project
        project = db.query(Project).filter(Project.id == data.project_id).first()
        if not project:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected project does not exist")
        cid = get_effective_company_id(user) if user else None
        if cid is not None and project.company_id != cid:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot create sprint in project belonging to another company")

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

    def update(self, db: Session, sprint_id: int, data: SprintUpdate, user=None):
        company_id = get_effective_company_id(user) if user else None
        sprint = self.get(db, sprint_id, company_id=company_id)
        if data.status_id is not None:
            st = db.query(SprintStatus).filter(SprintStatus.id == data.status_id).first()
            if not st:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid sprint status")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(sprint, field, value)
        db.commit()
        db.refresh(sprint)
        return sprint

    def delete(self, db: Session, sprint_id: int, user=None):
        company_id = get_effective_company_id(user) if user else None
        sprint = self.get(db, sprint_id, company_id=company_id)
        # Unlink issues before deleting
        db.query(Issue).filter(Issue.sprint_id == sprint_id).update({"sprint_id": None})
        db.delete(sprint)
        db.commit()

    def assign_issue(self, db: Session, sprint_id: int, issue_id: int, user):
        company_id = get_effective_company_id(user) if user else None
        sprint = self.get(db, sprint_id, company_id=company_id)
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
        if company_id is not None and getattr(issue, 'company_id', None) != company_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign issue from another company to sprint")
        if issue.project_id != sprint.project_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Issue and sprint must belong to the same project")

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
        company_id = get_effective_company_id(user) if user else None
        sprint = self.get(db, sprint_id, company_id=company_id)
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

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.issue import Issue
from app.models.user import User
from app.repositories.issue_repository import IssueRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.issue import IssueCreate, IssueUpdate


class IssueService:
    def __init__(self):
        self.repository = IssueRepository()
    def list(self, db: Session):
        print("services/issue_service.py Fetching all issues")
        return self.repository.list(db)
    def get(self, db: Session, issue_id: int):
        print(f"services/issue_service.py Fetching issue with ID {issue_id}")
        issue = self.repository.get(db, issue_id)
        if not issue:
            print("services/issue_service.py Issue not found")
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
        return issue
    def _validate_references(self, db: Session, data: IssueCreate):
        print(f"services/issue_service.py Validating references for issue: {data.title}")
        if not ProjectRepository().get(db, data.project_id):
            print("services/issue_service.py Selected project does not exist")
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected project does not exist")
        if data.assigned_to and not UserRepository().get_by_id(db, data.assigned_to):
            print("services/issue_service.py Selected assignee does not exist")
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected assignee does not exist")
    def create(self, db: Session, data: IssueCreate, user: User):
        print(f"services/issue_service.py Creating issue: {data.title}")
        self._validate_references(db, data)
        return self.repository.create(db, Issue(**data.model_dump(), reporter_id=user.id))
    def update(self, db: Session, issue_id: int, data: IssueUpdate):
        print(f"services/issue_service.py Updating issue with ID {issue_id}")
        self._validate_references(db, data); issue = self.get(db, issue_id)
        for field, value in data.model_dump().items():
            setattr(issue, field, value)
        db.commit(); db.refresh(issue)
        return self.repository.get(db, issue.id)
    def delete(self, db: Session, issue_id: int):
        print(f"services/issue_service.py Deleting issue with ID {issue_id}")
        self.repository.delete(db, self.get(db, issue_id))

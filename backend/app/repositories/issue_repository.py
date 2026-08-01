from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.issue import Issue


class IssueRepository:
    _options = (selectinload(Issue.project), selectinload(Issue.reporter))

    def list(self, db: Session) -> list[Issue]:
        print("repositories/issue_repository.py Fetching all issues from the database")
        return list(db.scalars(select(Issue).options(*self._options).order_by(Issue.created_at.desc())))

    def get(self, db: Session, issue_id: int) -> Issue | None:
        print(f"repositories/issue_repository.py Fetching issue with ID {issue_id} from the database")
        return db.scalar(select(Issue).options(*self._options).where(Issue.id == issue_id))

    def create(self, db: Session, issue: Issue) -> Issue:
        print(f"repositories/issue_repository.py Creating a new issue with title '{issue.title}' in the database")
        db.add(issue); db.commit(); db.refresh(issue)
        return self.get(db, issue.id)  # type: ignore[return-value]

    def delete(self, db: Session, issue: Issue) -> None:
        print(f"repositories/issue_repository.py Deleting issue with ID {issue.id} from the database")
        db.delete(issue); db.commit()

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.issue import Issue

class IssueRepository:
    _options = (selectinload(Issue.project), selectinload(Issue.reporter), selectinload(Issue.assignee))

    def list(self, db: Session, reporter_id: int | None = None, project_ids: list[int] | None = None) -> list[Issue]:
        print("repositories/issue_repository.py Fetching issues from the database")
        stmt = select(Issue).options(*self._options).where(Issue.is_deleted == False)
        if reporter_id is not None:
            stmt = stmt.where(Issue.reporter_id == reporter_id)
        if project_ids is not None:
            stmt = stmt.where(Issue.project_id.in_(project_ids))
        # Order by priority descending (Critical first), severity descending (Critical first),
        # status ascending (Open → In Progress → Resolved → Closed), then created_at descending (newest first)
        stmt = stmt.order_by(
            Issue.status_id.asc(),     # Open=1, In Progress=2, Resolved=3, Closed=4
            Issue.priority_id.desc(),  # Critical=4, High=3, Medium=2, Low=1
            Issue.severity_id.desc(),  # Critical=4, High=3, Medium=2, Low=1
            Issue.created_at.desc()    # Newest first
        )
        return list(db.scalars(stmt))

    def get(self, db: Session, issue_id: int) -> Issue | None:
        print(f"repositories/issue_repository.py Fetching issue with ID {issue_id} from the database")
        return db.scalar(select(Issue).options(*self._options).where(Issue.id == issue_id, Issue.is_deleted == False))

    def create(self, db: Session, issue: Issue) -> Issue:
        print(f"repositories/issue_repository.py Creating a new issue with title '{issue.title}' in the database")
        db.add(issue)
        db.commit()
        db.refresh(issue)
        return self.get(db, issue.id)

    def delete(self, db: Session, issue: Issue) -> None:
        print(f"repositories/issue_repository.py Soft-deleting issue with ID {issue.id} from the database")
        issue.is_deleted = True
        db.commit()

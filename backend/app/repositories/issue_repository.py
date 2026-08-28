from __future__ import annotations
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

    def find_similar(
        self,
        db: Session,
        embedding: list[float],
        exclude_issue_id: int | None = None,
        project_id: int | None = None,
        status_ids: list[int] | None = None,
        similarity_threshold: float = 0.60,
        limit: int = 10,
    ) -> list[tuple[Issue, float]]:
        """
        Find similar issues using pgvector cosine distance at the database level.
        Returns list of (Issue, similarity_score) tuples sorted by similarity descending.
        Cosine distance = 1 - cosine_similarity, so similarity = 1 - distance.
        """
        cosine_distance = Issue.embedding_vector.cosine_distance(embedding)
        max_distance = 1.0 - similarity_threshold

        stmt = (
            select(Issue, (1 - cosine_distance).label("similarity"))
            .options(*self._options)
            .where(
                Issue.is_deleted == False,
                Issue.is_active == True,
                Issue.embedding_vector.isnot(None),
                cosine_distance <= max_distance,
            )
        )

        if exclude_issue_id is not None:
            stmt = stmt.where(Issue.id != exclude_issue_id)
        if project_id is not None:
            stmt = stmt.where(Issue.project_id == project_id)
        if status_ids is not None:
            stmt = stmt.where(Issue.status_id.in_(status_ids))

        stmt = stmt.order_by(cosine_distance.asc()).limit(limit)

        results = db.execute(stmt).all()
        return [(row[0], float(row[1])) for row in results]

    def semantic_search(
        self,
        db: Session,
        embedding: list[float],
        exclude_issue_id: int | None = None,
        project_id: int | None = None,
        similarity_threshold: float = 0.60,
        limit: int = 20,
    ) -> list[tuple[Issue, float]]:
        """
        Search issues by semantic similarity to a query embedding.
        Uses pgvector cosine distance at the database level.
        Returns list of (Issue, similarity_score) tuples.
        """
        cosine_distance = Issue.embedding_vector.cosine_distance(embedding)
        max_distance = 1.0 - similarity_threshold

        stmt = (
            select(Issue, (1 - cosine_distance).label("similarity"))
            .options(*self._options)
            .where(
                Issue.is_deleted == False,
                Issue.is_active == True,
                Issue.embedding_vector.isnot(None),
                cosine_distance <= max_distance,
            )
        )

        if exclude_issue_id is not None:
            stmt = stmt.where(Issue.id != exclude_issue_id)
        if project_id is not None:
            stmt = stmt.where(Issue.project_id == project_id)

        stmt = stmt.order_by(cosine_distance.asc()).limit(limit)

        results = db.execute(stmt).all()
        return [(row[0], float(row[1])) for row in results]


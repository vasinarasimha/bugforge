from __future__ import annotations
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.issue import Issue

logger = logging.getLogger(__name__)

class IssueRepository:
    _options = (
        selectinload(Issue.project),
        selectinload(Issue.reporter),
        selectinload(Issue.assignee),
        selectinload(Issue.status),
        selectinload(Issue.priority),
        selectinload(Issue.severity),
        selectinload(Issue.category),
        selectinload(Issue.module),
        selectinload(Issue.sprint),
        selectinload(Issue.requesting_company),
        selectinload(Issue.team),
        selectinload(Issue.qa_verified_by),
        selectinload(Issue.assigned_qa),
    )

    def list(
        self,
        db: Session,
        reporter_id: int | None = None,
        project_ids: list[int] | None = None,
        company_id: int | None = None,
        issue_type: str | None = None,
        requesting_company_id: int | None = None,
        is_bugforge: bool = False,
        include_client_requests: bool = False,
    ) -> list[Issue]:
        logger.debug("Fetching issues from the database")
        stmt = select(Issue).options(*self._options).where(Issue.is_deleted == False)
        if company_id is not None:
            if is_bugforge:
                stmt = stmt.where((Issue.company_id == company_id) | (Issue.requesting_company_id.isnot(None)))
            elif include_client_requests:
                stmt = stmt.where((Issue.company_id == company_id) | (Issue.requesting_company_id == company_id))
            else:
                stmt = stmt.where(Issue.company_id == company_id)
        if requesting_company_id is not None and is_bugforge:
            stmt = stmt.where(Issue.requesting_company_id == requesting_company_id)
        if issue_type is not None:
            stmt = stmt.where(Issue.issue_type == issue_type)
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

    def get(self, db: Session, issue_id: int, company_id: int | None = None, is_bugforge: bool = False) -> Issue | None:
        logger.debug(f"Fetching issue with ID {issue_id} from the database")
        stmt = select(Issue).options(*self._options).where(Issue.id == issue_id, Issue.is_deleted == False)
        if company_id is not None:
            if is_bugforge:
                stmt = stmt.where((Issue.company_id == company_id) | (Issue.requesting_company_id.isnot(None)))
            else:
                stmt = stmt.where((Issue.company_id == company_id) | (Issue.requesting_company_id == company_id))
        return db.scalar(stmt)

    def create(self, db: Session, issue: Issue) -> Issue:
        logger.debug(f"Creating a new issue with title '{issue.title}' in the database")
        db.add(issue)
        db.commit()
        db.refresh(issue)
        return self.get(db, issue.id)

    def delete(self, db: Session, issue: Issue) -> None:
        logger.debug(f"Soft-deleting issue with ID {issue.id} from the database")
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
        company_id: int | None = None,
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

        if company_id is not None:
            stmt = stmt.where((Issue.company_id == company_id) | (Issue.requesting_company_id == company_id))
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
        company_id: int | None = None,
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

        if company_id is not None:
            stmt = stmt.where((Issue.company_id == company_id) | (Issue.requesting_company_id == company_id))
        if exclude_issue_id is not None:
            stmt = stmt.where(Issue.id != exclude_issue_id)
        if project_id is not None:
            stmt = stmt.where(Issue.project_id == project_id)

        stmt = stmt.order_by(cosine_distance.asc()).limit(limit)

        results = db.execute(stmt).all()
        return [(row[0], float(row[1])) for row in results]


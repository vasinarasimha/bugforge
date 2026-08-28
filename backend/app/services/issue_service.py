from __future__ import annotations
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.issue import Issue, IssueCategory, IssueModule
from app.models.user import User
from app.repositories.issue_repository import IssueRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

# Fields that affect the semantic meaning of an issue
SEMANTIC_FIELDS = {"title", "description", "category_id", "module_id", "issue_type"}


class IssueService:
    def __init__(self):
        self.repository = IssueRepository()

    def list(self, db: Session, reporter_id: int | None = None, project_ids: list[int] | None = None):
        return self.repository.list(db, reporter_id=reporter_id, project_ids=project_ids)

    def get(self, db: Session, issue_id: int):
        issue = self.repository.get(db, issue_id)
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
        return issue

    def _validate_references(self, db: Session, data: IssueCreate | IssueUpdate):
        if hasattr(data, 'project_id') and data.project_id is not None:
            if not ProjectRepository().get(db, data.project_id):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected project does not exist")
        if hasattr(data, 'assigned_to') and data.assigned_to:
            if not UserRepository().get_by_id(db, data.assigned_to):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected assignee does not exist")

    def _resolve_names_for_embedding(self, db: Session, category_id: int | None, module_id: int | None) -> tuple[str | None, str | None]:
        """Resolve category and module IDs to names for embedding text."""
        category_name = None
        module_name = None
        if category_id:
            cat = db.query(IssueCategory).filter(IssueCategory.id == category_id).first()
            if cat:
                category_name = cat.name
        if module_id:
            mod = db.query(IssueModule).filter(IssueModule.id == module_id).first()
            if mod:
                module_name = mod.name
        return category_name, module_name

    def _generate_embedding_safe(self, title: str, description: str, category: str | None = None, module: str | None = None, issue_type: str | None = None) -> list[float] | None:
        """Generate embedding with graceful error handling — never breaks the caller."""
        try:
            return embedding_service.embed_issue(title, description, category, module, issue_type)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def _generate_next_issue_key(self, db: Session, project_key: str) -> str:
        """
        Generate the next globally unique issue_key for the given project_key (e.g. 'E2E-1', 'E2E-2').
        Guarantees uniqueness against any existing records across the entire database, handling
        deleted issues, legacy records, or manual key entries safely.
        """
        prefix = (project_key or "ISSUE").strip().upper()
        prefix_pattern = f"{prefix}-%"
        
        # Query all issue keys starting with this prefix across the entire database
        matching_keys = db.query(Issue.issue_key).filter(Issue.issue_key.like(prefix_pattern)).all()
        
        max_num = 0
        existing_keys = set()
        for (k,) in matching_keys:
            if not k:
                continue
            existing_keys.add(k)
            parts = k.split("-", 1)
            if len(parts) == 2 and parts[0] == prefix:
                try:
                    num = int(parts[1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        
        candidate_num = max_num + 1
        while f"{prefix}-{candidate_num}" in existing_keys or db.query(Issue.id).filter(Issue.issue_key == f"{prefix}-{candidate_num}").first() is not None:
            candidate_num += 1
            
        return f"{prefix}-{candidate_num}"

    def create(self, db: Session, data: IssueCreate, user: User):
        self._validate_references(db, data)
        project = ProjectRepository().get(db, data.project_id)
        issue_key = self._generate_next_issue_key(db, project.key)

        issue_data = data.model_dump()

        # Resolve category/module names for richer embedding
        category_name, module_name = self._resolve_names_for_embedding(
            db, issue_data.get('category_id'), issue_data.get('module_id')
        )

        # Generate embedding for the issue
        embedding = self._generate_embedding_safe(
            title=issue_data.get('title', ''),
            description=issue_data.get('description', ''),
            category=category_name,
            module=module_name,
            issue_type=issue_data.get('issue_type'),
        )
        if embedding is not None:
            issue_data['embedding_vector'] = embedding

        return self.repository.create(db, Issue(**issue_data, reporter_id=user.id, issue_key=issue_key))

    def update(self, db: Session, issue_id: int, data: IssueUpdate, user: User):
        self._validate_references(db, data)
        issue = self.get(db, issue_id)

        # Flag to determine if we need to regenerate embedding
        regenerate_embedding = False

        from app.models.history import IssueHistory
        from app.models.issue import IssueStatus, IssuePriority, IssueSeverity, IssueCategory, IssueModule
        from app.models.user import User as UserModel
        
        for field, value in data.model_dump(exclude_unset=True).items():
            if isinstance(value, str) and value.strip() == '':
                value = None
            old_value = getattr(issue, field)
            if isinstance(old_value, str) and old_value.strip() == '':
                old_value = None
                
            if old_value != value:
                
                old_str, new_str = str(old_value) if old_value is not None else None, str(value) if value is not None else None
                
                if field == 'status_id':
                    old_s = db.query(IssueStatus).filter(IssueStatus.id == old_value).first()
                    new_s = db.query(IssueStatus).filter(IssueStatus.id == value).first()
                    old_str = old_s.name if old_s else old_str
                    new_str = new_s.name if new_s else new_str
                elif field == 'priority_id':
                    old_p = db.query(IssuePriority).filter(IssuePriority.id == old_value).first()
                    new_p = db.query(IssuePriority).filter(IssuePriority.id == value).first()
                    old_str = old_p.name if old_p else old_str
                    new_str = new_p.name if new_p else new_str
                elif field == 'severity_id':
                    old_sv = db.query(IssueSeverity).filter(IssueSeverity.id == old_value).first()
                    new_sv = db.query(IssueSeverity).filter(IssueSeverity.id == value).first()
                    old_str = old_sv.name if old_sv else old_str
                    new_str = new_sv.name if new_sv else new_str
                elif field == 'category_id':
                    old_c = db.query(IssueCategory).filter(IssueCategory.id == old_value).first()
                    new_c = db.query(IssueCategory).filter(IssueCategory.id == value).first()
                    old_str = old_c.name if old_c else old_str
                    new_str = new_c.name if new_c else new_str
                elif field == 'module_id':
                    old_m = db.query(IssueModule).filter(IssueModule.id == old_value).first()
                    new_m = db.query(IssueModule).filter(IssueModule.id == value).first()
                    old_str = old_m.name if old_m else old_str
                    new_str = new_m.name if new_m else new_str
                elif field == 'assigned_to':
                    old_u = db.query(UserModel).filter(UserModel.id == old_value).first()
                    new_u = db.query(UserModel).filter(UserModel.id == value).first()
                    old_str = old_u.full_name if old_u else old_str
                    new_str = new_u.full_name if new_u else new_str
                elif field == 'sprint_id':
                    from app.models.sprint import Sprint
                    old_sp = db.query(Sprint).filter(Sprint.id == old_value).first() if old_value else None
                    new_sp = db.query(Sprint).filter(Sprint.id == value).first() if value else None
                    old_str = old_sp.name if old_sp else None
                    new_str = new_sp.name if new_sp else None

                # Check if this field affects semantic meaning
                if field in SEMANTIC_FIELDS:
                    regenerate_embedding = True

                history = IssueHistory(
                    issue_id=issue.id,
                    user_id=user.id,
                    field_name=field,
                    old_value=old_str,
                    new_value=new_str
                )
                db.add(history)

            setattr(issue, field, value)
        

        # Regenerate embedding if any semantic field was updated
        if regenerate_embedding:
            category_name, module_name = self._resolve_names_for_embedding(
                db, issue.category_id, issue.module_id
            )
            embedding = self._generate_embedding_safe(
                title=issue.title,
                description=issue.description,
                category=category_name,
                module=module_name,
                issue_type=issue.issue_type,
            )
            if embedding is not None:
                issue.embedding_vector = embedding

        db.commit()
        db.refresh(issue)
        return self.repository.get(db, issue.id)

    def find_similar_issues(self, db: Session, issue_id: int, project_id: int | None = None):
        """Find issues similar to an existing issue using pgvector similarity."""
        settings = get_settings()
        issue = self.get(db, issue_id)

        if issue.embedding_vector is None:
            return []

        try:
            results = self.repository.find_similar(
                db,
                embedding=list(issue.embedding_vector),
                exclude_issue_id=issue.id,
                project_id=project_id or issue.project_id,
                similarity_threshold=settings.similarity_threshold,
                limit=settings.similar_defects_limit,
            )
            return self._format_similar_results(results, settings)
        except Exception as e:
            logger.error(f"Similar issue search failed: {e}")
            return []

    def find_similar_for_embedding(self, db: Session, embedding: list[float], exclude_issue_id: int | None = None, project_id: int | None = None):
        """Find issues similar to a given embedding vector (used during creation)."""
        settings = get_settings()
        try:
            results = self.repository.find_similar(
                db,
                embedding=embedding,
                exclude_issue_id=exclude_issue_id,
                project_id=project_id,
                similarity_threshold=settings.similarity_threshold,
                limit=settings.similar_defects_limit,
            )
            return self._format_similar_results(results, settings)
        except Exception as e:
            logger.error(f"Similar issue search failed: {e}")
            return []

    def semantic_search(self, db: Session, query: str, exclude_issue_id: int | None = None, project_id: int | None = None, limit: int | None = None):
        """Search issues using natural language query."""
        settings = get_settings()
        try:
            embedding = embedding_service.embed_query(query)
            if embedding is None:
                return []

            results = self.repository.semantic_search(
                db,
                embedding=embedding,
                exclude_issue_id=exclude_issue_id,
                project_id=project_id,
                similarity_threshold=settings.similarity_threshold,
                limit=limit or 20,
            )
            return self._format_similar_results(results, settings)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _format_similar_results(self, results: list[tuple[Issue, float]], settings) -> list[dict]:
        """Format similarity search results with labels and scores."""
        formatted = []
        for issue, similarity in results:
            if similarity >= settings.duplicate_threshold:
                label = "Potential Duplicate"
            else:
                label = "Similar Defect"

            formatted.append({
                "id": issue.id,
                "issue_key": issue.issue_key,
                "title": issue.title,
                "description": issue.description[:200] if issue.description else "",
                "status_id": issue.status_id,
                "status_name": issue.status.name if issue.status else "Unknown",
                "severity_id": issue.severity_id,
                "severity_name": issue.severity.name if issue.severity else "Unknown",
                "priority_id": issue.priority_id,
                "priority_name": issue.priority.name if issue.priority else "Unknown",
                "category_name": issue.category.name if getattr(issue, 'category', None) else None,
                "module_name": issue.module.name if getattr(issue, 'module', None) else None,
                "project_id": issue.project_id,
                "project_name": issue.project.name if getattr(issue, 'project', None) else "",
                "similarity_score": round(similarity, 4),
                "similarity_percent": round(similarity * 100, 1),
                "similarity_label": label,
            })
        return formatted

    def get_history(self, db: Session, issue_id: int):
        from app.models.history import IssueHistory
        from sqlalchemy.orm import selectinload
        return db.query(IssueHistory).options(selectinload(IssueHistory.user)).filter(IssueHistory.issue_id == issue_id).order_by(IssueHistory.created_at.desc()).all()

    def get_comments(self, db: Session, issue_id: int):
        from app.models.comment import IssueComment
        from sqlalchemy.orm import selectinload
        return db.query(IssueComment).options(selectinload(IssueComment.user)).filter(IssueComment.issue_id == issue_id).order_by(IssueComment.created_at.desc()).all()

    def create_comment(self, db: Session, issue_id: int, content: str, user: User):
        from app.models.comment import IssueComment
        issue = self.get(db, issue_id)
        comment = IssueComment(issue_id=issue.id, user_id=user.id, content=content)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    def delete(self, db: Session, issue_id: int, user: User):
        issue = self.get(db, issue_id)
        self.repository.delete(db, issue)

    def get_attachments(self, db: Session, issue_id: int):
        from app.models.attachment import IssueAttachment
        return db.query(IssueAttachment).filter(IssueAttachment.issue_id == issue_id).order_by(IssueAttachment.created_at.asc()).all()

    def add_attachment(self, db: Session, issue_id: int, filename: str, file_path: str, file_size: int | None, mime_type: str | None, user: User):
        from app.models.attachment import IssueAttachment
        self.get(db, issue_id)  # ensure issue exists
        att = IssueAttachment(
            issue_id=issue_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=user.id,
        )
        db.add(att)
        db.commit()
        db.refresh(att)
        return att

    def delete_attachment(self, db: Session, issue_id: int, attachment_id: int, user: User):
        from app.models.attachment import IssueAttachment
        att = db.query(IssueAttachment).filter(
            IssueAttachment.id == attachment_id,
            IssueAttachment.issue_id == issue_id
        ).first()
        if not att:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
        import os
        try:
            path = att.file_path.lstrip("/")
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        db.delete(att)
        db.commit()

    def track_issue_changes(self, db: Session, old_issue: Issue, new_issue: Issue, user_id: int):
        """Track changes between two issue objects and create history records."""
        from app.models.history import IssueHistory
        from app.models.issue import IssueStatus, IssuePriority, IssueSeverity, IssueCategory, IssueModule
        from app.models.user import User as UserModel
        from app.services.embedding_service import embedding_service

        # Flag to determine if we need to regenerate embedding
        regenerate_embedding = False

        # Get all fields from the Issue model
        fields = [column.name for column in Issue.__table__.columns]

        for field in fields:
            # Skip certain fields that shouldn't trigger history or are handled specially
            if field in ['id', 'issue_key', 'created_at', 'updated_at', 'is_deleted', 'embedding_vector']:
                continue

            old_value = getattr(old_issue, field, None)
            new_value = getattr(new_issue, field, None)

            # Handle empty strings
            if isinstance(old_value, str) and old_value.strip() == '':
                old_value = None
            if isinstance(new_value, str) and new_value.strip() == '':
                new_value = None

            if old_value != new_value:
                old_str, new_str = str(old_value) if old_value is not None else None, str(new_value) if new_value is not None else None

                # Handle special field types that need display names
                if field == 'status_id':
                    old_s = db.query(IssueStatus).filter(IssueStatus.id == old_value).first() if old_value is not None else None
                    new_s = db.query(IssueStatus).filter(IssueStatus.id == new_value).first() if new_value is not None else None
                    old_str = old_s.name if old_s else old_str
                    new_str = new_s.name if new_s else new_str
                elif field == 'priority_id':
                    old_p = db.query(IssuePriority).filter(IssuePriority.id == old_value).first() if old_value is not None else None
                    new_p = db.query(IssuePriority).filter(IssuePriority.id == new_value).first() if new_value is not None else None
                    old_str = old_p.name if old_p else old_str
                    new_str = new_p.name if new_p else new_str
                elif field == 'severity_id':
                    old_sv = db.query(IssueSeverity).filter(IssueSeverity.id == old_value).first() if old_value is not None else None
                    new_sv = db.query(IssueSeverity).filter(IssueSeverity.id == new_value).first() if new_value is not None else None
                    old_str = old_sv.name if old_sv else old_str
                    new_str = new_sv.name if new_sv else new_str
                elif field == 'category_id':
                    old_c = db.query(IssueCategory).filter(IssueCategory.id == old_value).first() if old_value is not None else None
                    new_c = db.query(IssueCategory).filter(IssueCategory.id == new_value).first() if new_value is not None else None
                    old_str = old_c.name if old_c else old_str
                    new_str = new_c.name if new_c else new_str
                elif field == 'module_id':
                    old_m = db.query(IssueModule).filter(IssueModule.id == old_value).first() if old_value is not None else None
                    new_m = db.query(IssueModule).filter(IssueModule.id == new_value).first() if new_value is not None else None
                    old_str = old_m.name if old_m else old_str
                    new_str = new_m.name if new_m else new_str
                elif field == 'assigned_to':
                    old_u = db.query(UserModel).filter(UserModel.id == old_value).first() if old_value is not None else None
                    new_u = db.query(UserModel).filter(UserModel.id == new_value).first() if new_value is not None else None
                    old_str = old_u.full_name if old_u else old_str
                    new_str = new_u.full_name if new_u else new_str
                elif field == 'sprint_id':
                    from app.models.sprint import Sprint
                    old_sp = db.query(Sprint).filter(Sprint.id == old_value).first() if old_value is not None else None
                    new_sp = db.query(Sprint).filter(Sprint.id == new_value).first() if new_value is not None else None
                    old_str = old_sp.name if old_sp else None
                    new_str = new_sp.name if new_sp else None

                # Check if this field affects semantic meaning
                if field in SEMANTIC_FIELDS:
                    regenerate_embedding = True

                history = IssueHistory(
                    issue_id=new_issue.id,
                    user_id=user_id,
                    field_name=field,
                    old_value=old_str,
                    new_value=new_str
                )
                db.add(history)

        # Regenerate embedding if any semantic field was updated
        if regenerate_embedding:
            category_name, module_name = self._resolve_names_for_embedding(
                db, new_issue.category_id, new_issue.module_id
            )
            embedding = self._generate_embedding_safe(
                title=new_issue.title,
                description=new_issue.description,
                category=category_name,
                module=module_name,
                issue_type=new_issue.issue_type,
            )
            if embedding is not None:
                new_issue.embedding_vector = embedding

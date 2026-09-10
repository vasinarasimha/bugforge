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

    def list(self, db: Session, reporter_id: int | None = None, project_ids: list[int] | None = None, company_id: int | None = None):
        return self.repository.list(db, reporter_id=reporter_id, project_ids=project_ids, company_id=company_id)

    def get(self, db: Session, issue_id: int, company_id: int | None = None):
        issue = self.repository.get(db, issue_id, company_id=company_id)
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
        return issue

    def delete(self, db: Session, issue_id: int, user: User):
        issue = self.get(db, issue_id, company_id=user.company_id)
        self.repository.delete(db, issue)

    def _validate_references(self, db: Session, data: IssueCreate | IssueUpdate, company_id: int | None = None):
        if hasattr(data, 'project_id') and data.project_id is not None:
            project = ProjectRepository().get(db, data.project_id)
            if not project:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected project does not exist")
            if company_id is not None and getattr(project, 'company_id', None) != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot reference project belonging to another company")
        if hasattr(data, 'assigned_to') and data.assigned_to:
            assignee = UserRepository().get_by_id(db, data.assigned_to)
            if not assignee:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected assignee does not exist")
            if company_id is not None and getattr(assignee, 'company_id', None) != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign issue to user from another company")
        if hasattr(data, 'sprint_id') and data.sprint_id:
            from app.models.sprint import Sprint
            sprint = db.query(Sprint).filter(Sprint.id == data.sprint_id).first()
            if not sprint:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected sprint does not exist")
            if company_id is not None and getattr(sprint, 'project', None) and getattr(sprint.project, 'company_id', None) != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign issue to sprint from another company")
        if hasattr(data, 'status_id') and data.status_id is not None:
            from app.models.issue import IssueStatus
            st = db.query(IssueStatus).filter(IssueStatus.id == data.status_id).first()
            if not st:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected status does not exist")
            if company_id is not None and st.company_id is not None and st.company_id != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot use status configured for another company")
            if not st.is_active:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Status '{st.name}' is deactivated and cannot be selected for issues")

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
        self._validate_references(db, data, company_id=user.company_id)
        project = ProjectRepository().get(db, data.project_id)
        issue_key = self._generate_next_issue_key(db, project.key)

        issue_data = data.model_dump()
        issue_data['company_id'] = user.company_id or getattr(project, 'company_id', 1) or 1

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
        issue = self.get(db, issue_id, company_id=user.company_id)
        self._validate_references(db, data, company_id=user.company_id)

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
                elif field == 'reporter_id':
                    old_u = db.query(UserModel).filter(UserModel.id == old_value).first()
                    new_u = db.query(UserModel).filter(UserModel.id == value).first()
                    old_str = old_u.full_name if old_u else old_str
                    new_str = new_u.full_name if new_u else new_str
                elif field == 'project_id':
                    from app.models.project import Project
                    old_p = db.query(Project).filter(Project.id == old_value).first() if old_value else None
                    new_p = db.query(Project).filter(Project.id == value).first() if value else None
                    old_str = old_p.name if old_p else old_str
                    new_str = new_p.name if new_p else new_str
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

    def find_similar_issues(self, db: Session, issue_id: int, project_id: int | None = None, company_id: int | None = None):
        """Find issues similar to an existing issue using pgvector similarity."""
        settings = get_settings()
        issue = self.get(db, issue_id, company_id=company_id)

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
                company_id=company_id,
            )
            return self._format_similar_results(results, settings)
        except Exception as e:
            logger.error(f"Similar issue search failed: {e}")
            return []

    def find_similar_for_embedding(self, db: Session, embedding: list[float], exclude_issue_id: int | None = None, project_id: int | None = None, company_id: int | None = None):
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
                company_id=company_id,
            )
            return self._format_similar_results(results, settings)
        except Exception as e:
            logger.error(f"Similar issue search failed: {e}")
            return []

    def semantic_search(self, db: Session, query: str, exclude_issue_id: int | None = None, project_id: int | None = None, limit: int | None = None, company_id: int | None = None):
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
                company_id=company_id,
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
                elif field == 'reporter_id':
                    old_u = db.query(UserModel).filter(UserModel.id == old_value).first() if old_value is not None else None
                    new_u = db.query(UserModel).filter(UserModel.id == new_value).first() if new_value is not None else None
                    old_str = old_u.full_name if old_u else old_str
                    new_str = new_u.full_name if new_u else new_str
                elif field == 'project_id':
                    from app.models.project import Project
                    old_p = db.query(Project).filter(Project.id == old_value).first() if old_value is not None else None
                    new_p = db.query(Project).filter(Project.id == new_value).first() if new_value is not None else None
                    old_str = old_p.name if old_p else old_str
                    new_str = new_p.name if new_p else new_str
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

    def _get_or_create_bugforge_company(self, db: Session):
        from app.models.company import Company
        bf = db.query(Company).filter(Company.name.ilike("BugForge")).first()
        if not bf:
            bf = Company(name="BugForge", domain="bugforge.internal", is_active=True)
            db.add(bf)
            db.commit()
            db.refresh(bf)
        return bf

    def _get_or_create_bugforge_project(self, db: Session):
        from app.models.project import Project
        bf_comp = self._get_or_create_bugforge_company(db)
        proj = db.query(Project).filter(Project.company_id == bf_comp.id, Project.is_active == True).first()
        if not proj:
            proj = Project(
                name="BugForge Platform Features",
                key="BFP",
                description="BugForge platform feature requests and customizations",
                company_id=bf_comp.id,
                is_active=True,
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
        return proj

    def submit_feature_request(
        self,
        db: Session,
        title: str,
        description: str,
        user: User,
        priority_id: int | None = None,
        severity_id: int | None = None,
    ) -> Issue:
        """
        Customer Company Admin submits a Feature Request to BugForge.
        Represented as an Issue with issue_type = 'Feature', company_id = 1 (BugForge),
        requesting_company_id = user.company_id, and reporter_id = user.id.
        """
        from app.models.issue import IssuePriority, IssueSeverity, IssueStatus
        from app.models.role import Role
        from app.services.notification_service import notification_service

        bf_comp = self._get_or_create_bugforge_company(db)
        bf_project = self._get_or_create_bugforge_project(db)
        issue_key = self._generate_next_issue_key(db, bf_project.key)

        # Initial status
        init_status = db.query(IssueStatus).filter(
            IssueStatus.company_id == bf_comp.id, IssueStatus.is_active == True, IssueStatus.is_initial == True
        ).first() or db.query(IssueStatus).filter(
            IssueStatus.company_id == bf_comp.id, IssueStatus.is_active == True, IssueStatus.name.in_(["Requested", "Open"])
        ).first() or db.query(IssueStatus).filter(IssueStatus.is_active == True).first()

        p_id = priority_id
        if not p_id:
            med_p = db.query(IssuePriority).filter(IssuePriority.is_active == True, IssuePriority.name == "Medium").first() or db.query(IssuePriority).first()
            p_id = med_p.id if med_p else 1

        s_id = severity_id
        if not s_id:
            med_s = db.query(IssueSeverity).filter(IssueSeverity.is_active == True, IssueSeverity.name == "Medium").first() or db.query(IssueSeverity).first()
            s_id = med_s.id if med_s else 1

        # Generate embedding
        embedding = self._generate_embedding_safe(
            title=title.strip(),
            description=description.strip(),
            issue_type="Feature",
        )

        feature_issue = Issue(
            issue_key=issue_key,
            title=title.strip(),
            description=description.strip(),
            issue_type="Feature",
            project_id=bf_project.id,
            reporter_id=user.id,
            company_id=bf_comp.id,  # Belongs to BugForge internal execution
            requesting_company_id=user.company_id,
            status_id=init_status.id,
            priority_id=p_id,
            severity_id=s_id,
            embedding_vector=embedding,
        )
        db.add(feature_issue)
        db.commit()
        db.refresh(feature_issue)

        # 1. Notify Super Admins
        super_admins = db.query(User).join(User.roles).filter(Role.name == "Super Admin", User.is_active == True).all()
        company_label = user.company_name or f"Company #{user.company_id}"
        for sa in super_admins:
            notification_service.create_notification(
                db,
                recipient_id=sa.id,
                actor_id=user.id,
                company_id=bf_comp.id,
                notification_type="FEATURE_REQUEST_SUBMITTED",
                title="New Feature Request",
                message=f"{user.full_name} ({company_label}) submitted Feature: {feature_issue.title}",
                entity_type="ISSUE",
                entity_id=feature_issue.id,
                link_url=f"/issues",
            )

        # 2. Notify Requesting Company Admin
        notification_service.create_notification(
            db,
            recipient_id=user.id,
            actor_id=user.id,
            company_id=user.company_id or bf_comp.id,
            notification_type="FEATURE_REQUEST_SUBMITTED",
            title="Feature Request Submitted",
            message=f"Feature request '{feature_issue.title}' ({feature_issue.issue_key}) has been submitted to BugForge.",
            entity_type="ISSUE",
            entity_id=feature_issue.id,
            link_url=f"/issues",
        )

        return self.repository.get(db, feature_issue.id)

    def assign_team(self, db: Session, issue_id: int, team_id: int, user: User) -> Issue:
        """
        Super Admin assigns a feature issue to an internal BugForge team.
        """
        from app.models.team import Team
        from app.models.issue import IssueStatus
        from app.services.notification_service import notification_service

        user_roles = [r.name for r in user.roles]
        if "Super Admin" not in user_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Super Admin can assign feature requests to internal teams")

        issue = self.repository.get(db, issue_id)
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")

        bf_comp = self._get_or_create_bugforge_company(db)
        team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
        if not team:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Selected internal team does not exist")
        if team.company_id != bf_comp.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assigned team must belong to BugForge organization")

        issue.team_id = team_id

        # Transition status to Assigned if currently open/initial
        assigned_status = db.query(IssueStatus).filter(
            IssueStatus.company_id == bf_comp.id,
            IssueStatus.is_active == True,
            IssueStatus.name.in_(["Assigned", "Under Review", "In Progress"])
        ).first()
        if assigned_status and issue.status and issue.status.category == "open":
            issue.status_id = assigned_status.id

        db.commit()
        db.refresh(issue)

        # Notify PM and TL of the assigned team
        recipients = set()
        if team.team_leader_id:
            recipients.add(team.team_leader_id)
        if team.project_manager_id:
            recipients.add(team.project_manager_id)

        for rid in recipients:
            notification_service.create_notification(
                db,
                recipient_id=rid,
                actor_id=user.id,
                company_id=bf_comp.id,
                notification_type="FEATURE_ASSIGNED_TO_TEAM",
                title="Feature Assigned to Team",
                message=f"{user.full_name} assigned Feature {issue.issue_key} to your team ({team.name})",
                entity_type="ISSUE",
                entity_id=issue.id,
                link_url=f"/issues",
            )

        return self.repository.get(db, issue.id)

    def assign_developer(self, db: Session, issue_id: int, developer_id: int | None, user: User) -> Issue:
        """
        PM/TL of the assigned team (or Super Admin/Admin) assigns work to a Developer.
        """
        from app.models.issue import IssueStatus
        from app.services.notification_service import notification_service

        issue = self.repository.get(db, issue_id)
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")

        user_roles = [r.name for r in user.roles]
        is_super_admin = "Super Admin" in user_roles
        is_admin = "Admin" in user_roles
        is_pm = any(r in ["Project Manager", "PM"] for r in user_roles)
        is_tl = any(r in ["Team Leader", "TL"] for r in user_roles)

        can_assign = is_super_admin or (is_admin and user.company_id == issue.company_id)
        if issue.team:
            if issue.team.team_leader_id == user.id or issue.team.project_manager_id == user.id:
                can_assign = True
        if (is_pm or is_tl) and issue.company_id == user.company_id:
            can_assign = True

        if not can_assign:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only authorized PM, TL, or Admin can assign developers")

        if developer_id is not None and developer_id > 0:
            dev = UserRepository().get_by_id(db, developer_id)
            if not dev:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected developer does not exist")
            if dev.company_id != issue.company_id and not is_super_admin:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Developer must belong to the same organization")

            issue.assigned_to = developer_id

            # Move to In Progress / In Development if in open status
            in_prog_status = db.query(IssueStatus).filter(
                IssueStatus.company_id == issue.company_id,
                IssueStatus.is_active == True,
                IssueStatus.category == "in_progress"
            ).first()
            if in_prog_status and issue.status and issue.status.category == "open":
                issue.status_id = in_prog_status.id

            db.commit()
            db.refresh(issue)

            notification_service.create_notification(
                db,
                recipient_id=developer_id,
                actor_id=user.id,
                company_id=issue.company_id,
                notification_type="FEATURE_ASSIGNED_TO_DEV",
                title="Work Assigned to You",
                message=f"Feature {issue.issue_key} ({issue.title}) was assigned to you",
                entity_type="ISSUE",
                entity_id=issue.id,
                link_url=f"/issues",
            )
        else:
            issue.assigned_to = None
            db.commit()
            db.refresh(issue)

        return self.repository.get(db, issue.id)

    def qa_verify(self, db: Session, issue_id: int, qa_state: str, notes: str | None, user: User) -> Issue:
        """
        QA verifies the feature implementation: Passed or Requires Rework.
        """
        from datetime import datetime, timezone
        from app.models.comment import IssueComment
        from app.models.issue import IssueStatus
        from app.services.notification_service import notification_service

        user_roles = [r.name for r in user.roles]
        can_qa = any(r in ["QA", "Admin", "Super Admin", "Project Manager", "Team Leader"] for r in user_roles)
        if not can_qa:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only QA or authorized roles can perform QA verification")

        issue = self.repository.get(db, issue_id)
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")

        issue.qa_state = qa_state
        issue.qa_verified_by_id = user.id
        issue.qa_verified_at = datetime.now(timezone.utc)

        comment_text = f"[QA Verification: {qa_state}]"
        if notes and notes.strip():
            comment_text += f" {notes.strip()}"
        comment = IssueComment(issue_id=issue.id, user_id=user.id, content=comment_text)
        db.add(comment)

        if qa_state == "Passed":
            res_status = db.query(IssueStatus).filter(
                IssueStatus.company_id == issue.company_id,
                IssueStatus.is_active == True,
                IssueStatus.category == "resolved"
            ).first()
            if not res_status:
                res_status = db.query(IssueStatus).filter(
                    IssueStatus.company_id == issue.company_id,
                    IssueStatus.is_active == True,
                    (IssueStatus.name.ilike("%resolved%")) | (IssueStatus.name.ilike("%verified%"))
                ).first()
            if not res_status:
                res_status = db.query(IssueStatus).filter(
                    IssueStatus.is_active == True,
                    IssueStatus.category == "resolved"
                ).first()
            if not res_status:
                res_status = db.query(IssueStatus).filter(
                    IssueStatus.is_active == True,
                    (IssueStatus.name.ilike("%resolved%")) | (IssueStatus.name.ilike("%verified%"))
                ).first()
            if not res_status:
                res_status = IssueStatus(
                    name="Resolved",
                    category="resolved",
                    color="#10b981",
                    company_id=issue.company_id,
                    is_active=True
                )
                db.add(res_status)
                db.flush()
            if res_status:
                issue.status_id = res_status.id
        elif qa_state == "Requires Rework":
            in_prog_status = db.query(IssueStatus).filter(
                IssueStatus.company_id == issue.company_id,
                IssueStatus.is_active == True,
                IssueStatus.category == "in_progress"
            ).first()
            if not in_prog_status:
                in_prog_status = db.query(IssueStatus).filter(
                    IssueStatus.company_id == issue.company_id,
                    IssueStatus.is_active == True,
                    IssueStatus.name.ilike("%progress%")
                ).first()
            if not in_prog_status:
                in_prog_status = db.query(IssueStatus).filter(
                    IssueStatus.is_active == True,
                    IssueStatus.category == "in_progress"
                ).first()
            if not in_prog_status:
                in_prog_status = db.query(IssueStatus).filter(
                    IssueStatus.is_active == True,
                    IssueStatus.name.ilike("%progress%")
                ).first()
            if not in_prog_status:
                in_prog_status = IssueStatus(
                    name="In Progress",
                    category="in_progress",
                    color="#8b5cf6",
                    company_id=issue.company_id,
                    is_active=True
                )
                db.add(in_prog_status)
                db.flush()
            if in_prog_status:
                issue.status_id = in_prog_status.id

            if issue.assigned_to:
                notification_service.create_notification(
                    db,
                    recipient_id=issue.assigned_to,
                    actor_id=user.id,
                    company_id=issue.company_id,
                    notification_type="FEATURE_QA_REWORK",
                    title="QA Verification: Rework Required",
                    message=f"QA requested rework on Feature {issue.issue_key}: {notes or 'Please review verification comments.'}",
                    entity_type="ISSUE",
                    entity_id=issue.id,
                    link_url=f"/issues",
                )

        db.commit()
        db.refresh(issue)
        return self.repository.get(db, issue.id)

    def notify_status_change(self, db: Session, issue: Issue, old_status_id: int, new_status_id: int, actor: User):
        """
        Send contextual notifications when an issue status changes significantly.
        """
        from app.models.issue import IssueStatus
        from app.models.role import Role
        from app.services.notification_service import notification_service

        new_status = db.query(IssueStatus).filter(IssueStatus.id == new_status_id).first()
        if not new_status:
            return

        # 1. Closed: notify requesting customer company admin
        if new_status.is_final or new_status.category == "closed" or new_status.name.lower() == "closed":
            if getattr(issue, "requesting_company_id", None) and issue.reporter_id:
                notification_service.create_notification(
                    db,
                    recipient_id=issue.reporter_id,
                    actor_id=actor.id,
                    company_id=issue.requesting_company_id,
                    notification_type="FEATURE_CLOSED",
                    title="Feature Implemented",
                    message=f"Feature {issue.issue_key} was successfully implemented",
                    entity_type="ISSUE",
                    entity_id=issue.id,
                    link_url=f"/issues",
                )

        # 2. Resolved / Ready for QA: notify QA
        elif new_status.category == "resolved" or "qa" in new_status.name.lower():
            qa_users = db.query(User).join(User.roles).filter(
                Role.name == "QA",
                User.is_active == True,
                User.company_id == issue.company_id
            ).all()
            for qu in qa_users:
                notification_service.create_notification(
                    db,
                    recipient_id=qu.id,
                    actor_id=actor.id,
                    company_id=issue.company_id,
                    notification_type="FEATURE_READY_FOR_QA",
                    title="Ready for QA Verification",
                    message=f"Feature {issue.issue_key} is ready for QA verification",
                    entity_type="ISSUE",
                    entity_id=issue.id,
                    link_url=f"/issues",
                )

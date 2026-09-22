from __future__ import annotations
import logging

from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_effective_company_id
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

# Fields to ignore completely from issue change history and UI timelines
IGNORED_HISTORY_FIELDS = {
    'id',
    'issue_key',
    'company_id',
    'company',
    'requesting_company_id',
    'requesting_company',
    'ai_root_cause_session_id',
    'developer_fixed_at',
    'qa_verified_at',
    'qa_verified_by_id',
    'created_at',
    'updated_at',
    'is_deleted',
    'embedding_vector',
}

# Fields that must never be modified via standard issue update payloads
FORBIDDEN_UPDATE_FIELDS = {
    'id',
    'company_id',
    'requesting_company_id',
    'created_at',
    'updated_at',
    'issue_key',
    'embedding_vector',
    'is_deleted',
    'developer_fixed_at',
    'qa_verified_at',
    'qa_verified_by_id',
    'ai_root_cause_session_id',
}


class IssueService:
    def __init__(self):
        self.repository = IssueRepository()

    def list(self, db: Session, reporter_id: int | None = None, project_ids: list[int] | None = None, company_id: int | None = None, is_bugforge: bool = False):
        return self.repository.list(db, reporter_id=reporter_id, project_ids=project_ids, company_id=company_id, is_bugforge=is_bugforge)

    def is_bugforge_user(self, db: Session, user: User) -> bool:
        if not user:
            return False
        user_roles = [r.name for r in getattr(user, 'roles', [])]
        if "Super Admin" in user_roles:
            return True
        if getattr(user, 'company', None) and getattr(user.company, 'name', '').lower() == "bugforge":
            return True
        bf_comp = self._get_or_create_bugforge_company(db)
        if user.company_id and user.company_id == bf_comp.id:
            return True
        return False

    def get(self, db: Session, issue_id: int, company_id: int | None = None, is_bugforge: bool = False):
        issue = self.repository.get(db, issue_id, company_id=company_id, is_bugforge=is_bugforge)
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
        return issue


    def delete(self, db: Session, issue_id: int, user: User):
        issue = self.get(db, issue_id, company_id=get_effective_company_id(user))
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
        if hasattr(data, 'assigned_qa_id') and data.assigned_qa_id:
            qa_user = UserRepository().get_by_id(db, data.assigned_qa_id)
            if not qa_user:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected QA assignee does not exist")
            if company_id is not None and getattr(qa_user, 'company_id', None) != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign QA user from another company")
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
        user_roles = [r.name for r in getattr(user, 'roles', [])]
        is_super_admin = "Super Admin" in user_roles

        # Requirement 7: For Feature requests submitted by customer/company admins,
        # canonical project must be BugForge (project = BugForge), requesting_company_id is set
        if data.issue_type == "Feature" and (user.company_id is not None and not is_super_admin):
            bf_comp = self._get_or_create_bugforge_company(db)
            bf_project = self._get_or_create_bugforge_project(db)
            data.project_id = bf_project.id
            self._validate_references(db, data, company_id=None)
            project = bf_project
            issue_data = data.model_dump()
            issue_data['project_id'] = bf_project.id
            issue_data['company_id'] = bf_comp.id
            issue_data['requesting_company_id'] = user.company_id
        else:
            self._validate_references(db, data, company_id=user.company_id)
            project = ProjectRepository().get(db, data.project_id)
            issue_data = data.model_dump()
            issue_data['company_id'] = user.company_id or getattr(project, 'company_id', 1) or 1

        issue_key = self._generate_next_issue_key(db, project.key)

        # Directly assign squad for BugForge project defects reported by BugForge employees
        bf_comp = self._get_or_create_bugforge_company(db)
        is_bf_project = bool(project and (project.company_id == bf_comp.id or project.key == "BF" or (getattr(project, 'name', '') and project.name.lower() == "bugforge")))
        is_bf_employee = bool(user.company_id == bf_comp.id or (getattr(user, 'company', None) and getattr(user.company, 'name', '').lower() == "bugforge") or (not user.company_id and is_super_admin))
        is_defect = bool(data.issue_type in ["Defect", "Bug"] or issue_data.get("issue_type") in ["Defect", "Bug"])

        if is_bf_project and is_bf_employee and is_defect and not issue_data.get('team_id'):
            user_team = self._get_user_team(db, user, bf_comp.id)
            if user_team:
                issue_data['team_id'] = user_team.id

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

        created_issue = self.repository.create(db, Issue(**issue_data, reporter_id=user.id, issue_key=issue_key))

        # Check if the created issue is a defect
        issue_type_str = str(
            getattr(created_issue, "issue_type", "")
            or getattr(data, "issue_type", "")
            or issue_data.get("issue_type", "")
        ).strip().lower()
        is_defect = (
            issue_type_str in ["defect", "bug"]
            or bool(getattr(created_issue, "is_defect", False))
            or bool(getattr(data, "is_defect", False))
        )

        # Explicit guard: non-defect issues must not enter the notification path
        if is_defect:
            if not project and getattr(created_issue, "project_id", None):
                project = ProjectRepository().get(db, created_issue.project_id)

            if project:
                from app.services.notification_service import notification_service
                recipients = set()

                # Team-assigned PM and TL
                team = getattr(project, "team", None)
                if team:
                    pm_id = getattr(team, "project_manager_id", None)
                    if isinstance(pm_id, int) and not isinstance(pm_id, bool):
                        recipients.add(pm_id)
                    tl_id = getattr(team, "team_leader_id", None)
                    if isinstance(tl_id, int) and not isinstance(tl_id, bool):
                        recipients.add(tl_id)

                # Direct project PM and TL
                pm_id = getattr(project, "project_manager_id", None)
                if isinstance(pm_id, int) and not isinstance(pm_id, bool):
                    recipients.add(pm_id)
                tl_id = getattr(project, "team_leader_id", None)
                if isinstance(tl_id, int) and not isinstance(tl_id, bool):
                    recipients.add(tl_id)

                # Ensure only non-None valid integer recipients
                recipients = {r for r in recipients if r is not None and isinstance(r, int) and not isinstance(r, bool)}

                comp_id = getattr(created_issue, "company_id", None)
                if not isinstance(comp_id, int) or isinstance(comp_id, bool):
                    comp_id = getattr(project, "company_id", None)
                if not isinstance(comp_id, int) or isinstance(comp_id, bool):
                    comp_id = getattr(user, "company_id", 1)
                if not isinstance(comp_id, int) or isinstance(comp_id, bool):
                    comp_id = 1

                proj_name = str(getattr(project, "name", "Project"))
                issue_title = str(getattr(created_issue, "title", "Defect"))
                issue_key_str = str(getattr(created_issue, "issue_key", "DEFECT"))
                issue_id = getattr(created_issue, "id", None)
                if not isinstance(issue_id, int) or isinstance(issue_id, bool):
                    issue_id = None

                for rid in recipients:
                    notification_service.create_notification(
                        db,
                        recipient_id=rid,
                        actor_id=user.id if isinstance(getattr(user, "id", None), int) else None,
                        company_id=comp_id,
                        notification_type="DEFECT_CREATED",
                        title="New Defect Created: Assign Developer & QA",
                        message=f"New defect '{issue_title}' ({issue_key_str}) created in project '{proj_name}'. Please assign a Developer and QA.",
                        entity_type="ISSUE",
                        entity_id=issue_id,
                        link_url=f"/issues/{issue_id}" if issue_id else None,
                    )
        else:
            return created_issue

        return created_issue

    def update(self, db: Session, issue_id: int, data: IssueUpdate, user: User):
        issue = self.get(db, issue_id, company_id=user.company_id)
        self._validate_references(db, data, company_id=user.company_id)

        # Flag to determine if we need to regenerate embedding
        regenerate_embedding = False

        from app.models.history import IssueHistory
        from app.models.issue import IssueStatus, IssuePriority, IssueSeverity, IssueCategory, IssueModule
        from app.models.user import User as UserModel
        
        dumped_data = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        for field, value in dumped_data.items():
            if field in FORBIDDEN_UPDATE_FIELDS or field in IGNORED_HISTORY_FIELDS:
                continue
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
                    if new_s and (new_s.name == "Resolved" or new_s.category == "resolved"):
                        if not getattr(issue, "developer_fixed_at", None):
                            from datetime import datetime, timezone
                            issue.developer_fixed_at = datetime.now(timezone.utc)
                    elif new_s and new_s.category in ("open", "in_progress"):
                        issue.developer_fixed_at = None
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
                elif field == 'assigned_qa_id':
                    old_u = db.query(UserModel).filter(UserModel.id == old_value).first() if old_value else None
                    new_u = db.query(UserModel).filter(UserModel.id == value).first() if value else None
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

        # Synchronize CustomizationRequest status if this issue is linked to one
        from app.models.customization_request import CustomizationRequest
        custom_req = db.query(CustomizationRequest).filter(CustomizationRequest.linked_issue_id == issue.id).first()
        if custom_req:
            status_obj = db.query(IssueStatus).filter(IssueStatus.id == issue.status_id).first() if issue.status_id else None
            if status_obj:
                if status_obj.name in ["Resolved", "Closed"] or getattr(status_obj, 'category', '') in ["resolved", "closed"]:
                    custom_req.status = "Implemented"
                elif status_obj.name in ["In Progress", "In Development"] or getattr(status_obj, 'category', '') == "in_progress":
                    if custom_req.status in ["Pending", "Under Review"]:
                        custom_req.status = "Under Review"

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

    def hybrid_search(
        self,
        db: Session,
        query: str,
        user: User,
        project_id: int | None = None,
        status_id: int | None = None,
        issue_type: str | None = None,
        requesting_company_id: int | None = None,
        reporter_id: int | None = None,
        limit: int = 50,
    ) -> list[Issue]:
        """
        Unified Hybrid Search combining keyword and semantic/vector search with tenant safety.
        - Keyword search: matching issue_key, title, description with SQL ILIKE
        - Semantic search: pgvector cosine distance on embedding_vector
        - Graceful degradation: if embedding fails, keyword search results are still returned
        - Strict tenant isolation: company filters applied at database query level
        - Merges, scores, ranks and deduplicates results by Issue.id
        """
        user_roles = [r.name for r in getattr(user, 'roles', [])]
        is_super_admin = "Super Admin" in user_roles
        user_company_id = getattr(user, 'company_id', None)

        clean_query = (query or "").strip()
        is_bf = self.is_bugforge_user(db, user)
        if not clean_query:
            # Empty search behavior: return normal issue list
            return self.repository.list(
                db,
                reporter_id=reporter_id,
                project_ids=[project_id] if project_id else None,
                company_id=user_company_id,
                issue_type=issue_type,
                requesting_company_id=requesting_company_id,
                is_bugforge=is_bf,
            )

        # 1. Keyword search (DB-level with strict tenant filtering)
        kw_stmt = (
            select(Issue)
            .options(*self.repository._options)
            .where(Issue.is_deleted == False, Issue.is_active == True)
        )
        if not is_super_admin and user_company_id is not None:
            if is_bf:
                kw_stmt = kw_stmt.where(
                    (Issue.company_id == user_company_id) | (Issue.requesting_company_id.isnot(None))
                )
            else:
                kw_stmt = kw_stmt.where(Issue.company_id == user_company_id)
        if requesting_company_id is not None and is_bf:
            kw_stmt = kw_stmt.where(Issue.requesting_company_id == requesting_company_id)

        if reporter_id is not None:
            kw_stmt = kw_stmt.where(Issue.reporter_id == reporter_id)
        if project_id is not None:
            kw_stmt = kw_stmt.where(Issue.project_id == project_id)
        if status_id is not None:
            kw_stmt = kw_stmt.where(Issue.status_id == status_id)
        if issue_type is not None:
            kw_stmt = kw_stmt.where(Issue.issue_type == issue_type)

        q_term = f"%{clean_query}%"
        kw_conditions = [
            Issue.issue_key.ilike(q_term),
            Issue.title.ilike(q_term),
            Issue.description.ilike(q_term),
        ]
        parsed_id = None
        if clean_query.lstrip("#").isdigit():
            parsed_id = int(clean_query.lstrip("#"))
            kw_conditions.append(Issue.id == parsed_id)

        kw_stmt = kw_stmt.where(or_(*kw_conditions))
        keyword_issues = list(db.scalars(kw_stmt))

        # 2. Semantic vector search (DB-level with strict tenant filtering)
        semantic_scored: list[tuple[Issue, float]] = []
        try:
            embedding = embedding_service.embed_query(clean_query)
            if embedding is not None:
                cid = None if is_super_admin else user_company_id
                raw_sem = self.repository.semantic_search(
                    db,
                    embedding=embedding,
                    project_id=project_id,
                    company_id=cid,
                    limit=limit or 30,
                    similarity_threshold=0.40,
                )
                for iss, score in raw_sem:
                    if status_id is not None and iss.status_id != status_id:
                        continue
                    if issue_type is not None and iss.issue_type != issue_type:
                        continue
                    if requesting_company_id is not None and iss.requesting_company_id != requesting_company_id:
                        continue
                    if reporter_id is not None and iss.reporter_id != reporter_id:
                        continue
                    semantic_scored.append((iss, score))
        except Exception as e:
            logger.warning(f"Semantic search service unavailable during hybrid search: {e}")

        # 3. Combine, rank and deduplicate
        combined: dict[int, dict] = {}
        q_lower = clean_query.lower()

        for iss in keyword_issues:
            score = 0.0
            if parsed_id is not None and iss.id == parsed_id:
                score += 150.0  # Direct ID match: highest priority

            key_lower = iss.issue_key.lower() if iss.issue_key else ""
            title_lower = iss.title.lower() if iss.title else ""
            desc_lower = iss.description.lower() if iss.description else ""

            if key_lower == q_lower:
                score += 100.0
            elif q_lower in key_lower:
                score += 60.0

            if title_lower == q_lower:
                score += 80.0
            elif q_lower in title_lower:
                score += 45.0

            if q_lower in desc_lower:
                score += 15.0

            combined[iss.id] = {
                "issue": iss,
                "score": score,
                "matched_kw": True,
                "matched_sem": False,
            }

        for iss, sim in semantic_scored:
            sem_boost = float(sim) * 50.0
            if iss.id in combined:
                # Matched both keyword and semantic! Boost significantly
                combined[iss.id]["score"] += sem_boost + 25.0
                combined[iss.id]["matched_sem"] = True
            else:
                combined[iss.id] = {
                    "issue": iss,
                    "score": sem_boost,
                    "matched_kw": False,
                    "matched_sem": True,
                }

        sorted_items = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        return [item["issue"] for item in sorted_items[:limit]]

    def get_history(self, db: Session, issue_id: int, company_id: int | None = None):
        from app.models.history import IssueHistory
        from sqlalchemy.orm import selectinload
        self.get(db, issue_id, company_id=company_id)
        return (
            db.query(IssueHistory)
            .options(selectinload(IssueHistory.user))
            .filter(
                IssueHistory.issue_id == issue_id,
                IssueHistory.field_name.notin_(IGNORED_HISTORY_FIELDS)
            )
            .order_by(IssueHistory.created_at.desc())
            .all()
        )

    def get_comments(self, db: Session, issue_id: int, company_id: int | None = None):
        from app.models.comment import IssueComment
        from sqlalchemy.orm import selectinload
        self.get(db, issue_id, company_id=company_id)
        return db.query(IssueComment).options(selectinload(IssueComment.user)).filter(IssueComment.issue_id == issue_id).order_by(IssueComment.created_at.desc()).all()

    def create_comment(self, db: Session, issue_id: int, content: str, user: User):
        from app.models.comment import IssueComment
        issue = self.get(db, issue_id, company_id=get_effective_company_id(user))
        comment = IssueComment(issue_id=issue.id, user_id=user.id, content=content)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    def get_attachments(self, db: Session, issue_id: int, company_id: int | None = None):
        from app.models.attachment import IssueAttachment
        self.get(db, issue_id, company_id=company_id)
        return db.query(IssueAttachment).filter(IssueAttachment.issue_id == issue_id).order_by(IssueAttachment.created_at.asc()).all()

    def add_attachment(self, db: Session, issue_id: int, filename: str, file_path: str, file_size: int | None, mime_type: str | None, user: User):
        from app.models.attachment import IssueAttachment
        self.get(db, issue_id, company_id=get_effective_company_id(user))  # ensure issue exists and belongs to company
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
        self.get(db, issue_id, company_id=get_effective_company_id(user))  # ensure issue exists and belongs to company
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
            # Skip internal/system fields that shouldn't trigger history
            if field in IGNORED_HISTORY_FIELDS:
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
        proj = db.query(Project).filter(
            Project.company_id == bf_comp.id,
            Project.key == "BF",
            Project.is_active == True
        ).first()
        if not proj:
            proj = db.query(Project).filter(
                Project.company_id == bf_comp.id,
                Project.name == "BugForge",
                Project.is_active == True
            ).first()
            if proj and proj.key != "BF":
                proj.key = "BF"
                db.commit()
                db.refresh(proj)
        if not proj:
            from app.models.user import User
            admin_user = db.query(User).filter(User.company_id == bf_comp.id).first()
            if not admin_user:
                admin_user = db.query(User).first()
            if not admin_user:
                admin_user = User(
                    full_name="BugForge Admin",
                    email="admin@bugforge.internal",
                    password_hash="mock_hash",
                    company_id=bf_comp.id,
                    is_active=True
                )
                db.add(admin_user)
                db.flush()

            proj = Project(
                name="BugForge",
                key="BF",
                description="BugForge platform feature requests and customizations",
                company_id=bf_comp.id,
                is_active=True,
                created_by=admin_user.id,
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
        elif proj.name != "BugForge":
            proj.name = "BugForge"
            db.commit()
            db.refresh(proj)
        return proj

    def _get_user_team(self, db: Session, user: User, company_id: int | None = None):
        from app.models.team import Team, TeamMember
        from sqlalchemy import or_
        query = db.query(Team).outerjoin(Team.members).filter(Team.is_active == True)
        if company_id is not None:
            query = query.filter(Team.company_id == company_id)
        query = query.filter(
            or_(
                TeamMember.user_id == user.id,
                Team.team_leader_id == user.id,
                Team.project_manager_id == user.id,
            )
        )
        return query.first()

    def submit_feature_request(
        self,
        db: Session,
        title: str,
        description: str,
        user: User,
        priority_id: int | None = None,
        severity_id: int | None = None,
        issue_type: str = "Feature",
    ) -> Issue:
        """
        Customer Company Admin submits a Feature or Defect/Issue Request to BugForge.
        Represented as an Issue with issue_type in ('Feature', 'Defect'), company_id = BugForge company,
        project_id = BugForge project, requesting_company_id = user.company_id, and reporter_id = user.id.
        """
        from app.models.issue import IssuePriority, IssueSeverity, IssueStatus
        from app.models.role import Role
        from app.services.notification_service import notification_service

        resolved_type = "Defect" if issue_type == "Defect" else "Feature"
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
            issue_type=resolved_type,
        )

        feature_issue = Issue(
            issue_key=issue_key,
            title=title.strip(),
            description=description.strip(),
            issue_type=resolved_type,
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
        notification_type = "CLIENT_DEFECT_SUBMITTED" if resolved_type == "Defect" else "FEATURE_REQUEST_SUBMITTED"
        notification_title = f"New Client {resolved_type} Request"
        for sa in super_admins:
            notification_service.create_notification(
                db,
                recipient_id=sa.id,
                actor_id=user.id,
                company_id=bf_comp.id,
                notification_type=notification_type,
                title=notification_title,
                message=f"{user.full_name} ({company_label}) submitted {resolved_type}: {feature_issue.title}",
                entity_type="ISSUE",
                entity_id=feature_issue.id,
                link_url=f"/issues/{feature_issue.id}",
            )

        # 2. Notify Requesting Company Admin
        notification_service.create_notification(
            db,
            recipient_id=user.id,
            actor_id=user.id,
            company_id=user.company_id or bf_comp.id,
            notification_type=notification_type,
            title=f"Client {resolved_type} Request Submitted",
            message=f"{resolved_type} request '{feature_issue.title}' ({feature_issue.issue_key}) has been submitted to BugForge.",
            entity_type="ISSUE",

            entity_id=feature_issue.id,
            link_url=f"/issues/{feature_issue.id}",
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
                link_url=f"/issues/{issue.id}",
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
                link_url=f"/issues/{issue.id}",
            )
        else:
            issue.assigned_to = None
            db.commit()
            db.refresh(issue)

        return self.repository.get(db, issue.id)

    def assign_qa(self, db: Session, issue_id: int, qa_id: int | None, user: User) -> Issue:
        """
        PM/TL/Admin/Super Admin (or QA) assigns an issue to a QA engineer.
        """
        from app.models.history import IssueHistory
        from app.models.user import User as UserModel
        from app.services.notification_service import notification_service

        issue = self.repository.get(db, issue_id)
        if not issue:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")

        user_roles = [r.name for r in user.roles]
        is_super_admin = "Super Admin" in user_roles
        is_admin = "Admin" in user_roles
        is_pm = any(r in ["Project Manager", "PM"] for r in user_roles)
        is_tl = any(r in ["Team Leader", "TL"] for r in user_roles)
        is_qa = "QA" in user_roles

        can_assign = is_super_admin or (is_admin and user.company_id == issue.company_id) or is_qa
        if issue.team:
            if issue.team.team_leader_id == user.id or issue.team.project_manager_id == user.id:
                can_assign = True
        if (is_pm or is_tl) and issue.company_id == user.company_id:
            can_assign = True

        if not can_assign:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only authorized PM, TL, Admin, or QA can assign QA engineers")

        old_qa_id = issue.assigned_qa_id
        old_qa_name = issue.assigned_qa.full_name if getattr(issue, 'assigned_qa', None) else None

        if qa_id is not None and qa_id > 0:
            qa_user = UserRepository().get_by_id(db, qa_id)
            if not qa_user:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected QA engineer does not exist")
            if qa_user.company_id != issue.company_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "QA engineer must belong to the same organization")

            issue.assigned_qa_id = qa_id
            new_qa_name = qa_user.full_name
        else:
            issue.assigned_qa_id = None
            new_qa_name = None

        # Track in history
        if old_qa_id != issue.assigned_qa_id:
            history = IssueHistory(
                issue_id=issue.id,
                user_id=user.id,
                field_name="assigned_qa_id",
                old_value=old_qa_name,
                new_value=new_qa_name
            )
            db.add(history)

        db.commit()
        db.refresh(issue)

        if qa_id is not None and qa_id > 0 and qa_id != user.id:
            notification_service.create_notification(
                db,
                recipient_id=qa_id,
                actor_id=user.id,
                company_id=issue.company_id,
                notification_type="QA_ASSIGNED",
                title="QA Verification Assigned",
                message=f"You have been assigned as QA for {issue.issue_key} ({issue.title})",
                entity_type="ISSUE",
                entity_id=issue.id,
                link_url=f"/issues/{issue.id}",
            )

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
                    link_url=f"/issues/{issue.id}",
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
        old_status = db.query(IssueStatus).filter(IssueStatus.id == old_status_id).first() if old_status_id else None

        # 1. Closed: notify requesting customer company admin
        if (new_status.category == "closed" or new_status.name.lower() == "closed" or (new_status.is_final and new_status.category != "resolved" and new_status.name.lower() != "resolved")):
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
                    link_url=f"/issues/{issue.id}",
                )

        # 2. Resolved / Ready for QA: notify QA
        elif new_status.category == "resolved" or new_status.name.lower() == "resolved" or "qa" in new_status.name.lower():
            label = "Feature" if getattr(issue, "issue_type", "") == "Feature" else "Defect"
            if getattr(issue, "assigned_qa_id", None):
                # If QA is selected then only the report should be sent only to the particular QA to test it
                notification_service.create_notification(
                    db,
                    recipient_id=issue.assigned_qa_id,
                    actor_id=actor.id,
                    company_id=issue.company_id,
                    notification_type="FEATURE_READY_FOR_QA",
                    title="Ready for QA Verification",
                    message=f"{label} {issue.issue_key} was resolved and is ready for your verification",
                    entity_type="ISSUE",
                    entity_id=issue.id,
                    link_url=f"/issues/{issue.id}",
                )
            else:
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
                        message=f"{label} {issue.issue_key} is ready for QA verification",
                        entity_type="ISSUE",
                        entity_id=issue.id,
                        link_url=f"/issues/{issue.id}",
                    )

        # 3. QA marks as Unresolved / Rework: status moved from Resolved back to In Progress / Open
        elif (
            (new_status.category in ("in_progress", "open") or new_status.name.lower() in ("in progress", "rework", "unresolved"))
            and (old_status and (old_status.category == "resolved" or old_status.name.lower() in ("resolved", "verified")))
        ):
            label = "Feature" if getattr(issue, "issue_type", "") == "Feature" else "Defect"
            if getattr(issue, "assigned_to", None):
                notification_service.create_notification(
                    db,
                    recipient_id=issue.assigned_to,
                    actor_id=actor.id,
                    company_id=issue.company_id,
                    notification_type="FEATURE_QA_REWORK",
                    title="QA Verification: Unresolved / Rework Required",
                    message=f"QA marked {label} {issue.issue_key} as Unresolved. Please review and fix the defect.",
                    entity_type="ISSUE",
                    entity_id=issue.id,
                    link_url=f"/issues/{issue.id}",
                )

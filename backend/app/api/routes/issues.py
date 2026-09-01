import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity, IssueCategory, IssueModule
from app.schemas.issue import (
    IssueCreate, IssueResponse, IssueUpdate,
    IssueStatusResponse, IssuePriorityResponse, IssueSeverityResponse,
    IssueCategoryResponse, IssueModuleResponse,
    IssueCommentCreate, IssueCommentResponse, IssueHistoryResponse,
    SimilarIssueResponse, IssueCreateResponse, SemanticSearchRequest, SemanticSearchResponse,
)
from app.schemas.attachment import IssueAttachmentResponse
from app.services.issue_service import IssueService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["Issues"])
service = IssueService()

def serialize(i):
    return {
        "id": i.id,
        "issue_key": i.issue_key,
        "title": i.title,
        "description": i.description,
        "issue_type": i.issue_type,
        "status_id": i.status_id,
        "status_name": i.status.name if i.status else "Unknown",
        "priority_id": i.priority_id,
        "priority_name": i.priority.name if i.priority else "Unknown",
        "severity_id": i.severity_id,
        "severity_name": i.severity.name if i.severity else "Unknown",
        "category_id": i.category_id,
        "category_name": i.category.name if getattr(i, 'category', None) else None,
        "module_id": i.module_id,
        "module_name": i.module.name if getattr(i, 'module', None) else None,
        "environment": i.environment,
        "browser": i.browser,
        "operating_system": i.operating_system,
        "reproduction_steps": i.reproduction_steps,
        "expected_behavior": i.expected_behavior,
        "actual_behavior": i.actual_behavior,
        "attachment_path": i.attachment_path,
        "sprint_id": i.sprint_id,
        "sprint_name": i.sprint.name if getattr(i, 'sprint', None) else None,
        "project_id": i.project_id,
        "project_name": i.project.name if getattr(i, 'project', None) else "",
        "reporter_id": i.reporter_id,
        "reporter_name": i.reporter.full_name if getattr(i, 'reporter', None) else "",
        "assigned_to": i.assigned_to,
        "assignee": i.assignee.full_name if getattr(i, 'assignee', None) else None,
        "ai_root_cause_session_id": getattr(i, 'ai_root_cause_session_id', None),
        "created_at": i.created_at,
        "updated_at": i.updated_at,
        "is_active": i.is_active
    }

@router.get("/statuses", response_model=list[IssueStatusResponse])
async def list_statuses(db: Annotated[Session, Depends(get_db)]):
    return db.query(IssueStatus).filter(IssueStatus.is_active == True).all()

@router.get("/priorities", response_model=list[IssuePriorityResponse])
async def list_priorities(db: Annotated[Session, Depends(get_db)]):
    return db.query(IssuePriority).filter(IssuePriority.is_active == True).all()

@router.get("/severities", response_model=list[IssueSeverityResponse])
async def list_severities(db: Annotated[Session, Depends(get_db)]):
    return db.query(IssueSeverity).filter(IssueSeverity.is_active == True).all()

@router.get("/categories", response_model=list[IssueCategoryResponse])
async def list_categories(db: Annotated[Session, Depends(get_db)]):
    return db.query(IssueCategory).filter(IssueCategory.is_active == True).all()

@router.get("/modules", response_model=list[IssueModuleResponse])
async def list_modules(db: Annotated[Session, Depends(get_db)]):
    return db.query(IssueModule).filter(IssueModule.is_active == True).all()


# ── Semantic Search & Similarity Endpoints ──

@router.post("/semantic-search", response_model=list[SemanticSearchResponse])
async def semantic_search(
    data: SemanticSearchRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """
    Search issues using natural-language semantic query.
    Returns ranked results by similarity score.
    """
    try:
        results = service.semantic_search(
            db, query=data.query, project_id=data.project_id, limit=data.limit
        )
        return results
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Semantic search temporarily unavailable")


class SearchRequest(BaseModel):
    title: str
    description: str
    project_id: int | None = None
    exclude_issue_id: int | None = None

@router.post("/search", response_model=list[dict])
async def search_issues(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    search_request: SearchRequest,
):
    """
    Search for similar issues by title and description.
    Uses pgvector cosine similarity at the database level.
    Backward-compatible with existing frontend usage.
    """
    from app.services.embedding_service import embedding_service

    try:
        embedding = embedding_service.embed_issue(search_request.title, search_request.description)
        if embedding is None:
            return []

        results = service.find_similar_for_embedding(
            db,
            embedding=embedding,
            exclude_issue_id=search_request.exclude_issue_id,
            project_id=search_request.project_id
        )
        # Return in backward-compatible format: [{issue: {...}, similarity: float}]
        return [{"issue": serialize(service.get(db, r["id"])), "similarity": r["similarity_score"]} for r in results]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Search temporarily unavailable")


# ── CRUD Endpoints ──

@router.get("", response_model=list[IssueResponse])
async def list_issues(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    user_roles = [r.name for r in user.roles]
    reporter_id = user.id if "Reporter" in user_roles and "Admin" not in user_roles and "Project Manager" not in user_roles and "Team Leader" not in user_roles and "QA" not in user_roles else None
    return [serialize(i) for i in service.list(db, reporter_id=reporter_id)]

@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: int, db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    return serialize(service.get(db, issue_id))

@router.post("", response_model=IssueCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(data: IssueCreate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    """
    Create a new issue and return it along with any similar existing issues found.
    The similar_issues list helps users identify potential duplicates.
    """
    created = service.create(db, data, user)
    serialized = serialize(created)

    # Find similar issues (graceful — never blocks creation)
    similar_issues = []
    try:
        if created.embedding_vector is not None:
            similar_issues = service.find_similar_for_embedding(
                db,
                embedding=list(created.embedding_vector),
                exclude_issue_id=created.id,
                project_id=created.project_id,
            )
    except Exception as e:
        logger.error(f"Similar issue detection during creation failed: {e}")

    return {"issue": serialized, "similar_issues": similar_issues}

@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(issue_id: int, data: IssueUpdate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    return serialize(service.update(db, issue_id, data, user))


class IssueStatusUpdate(BaseModel):
    status_id: int
    root_cause: str | None = None
    resolution: str | None = None
    comment: str | None = None

@router.patch("/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(issue_id: int, data: IssueStatusUpdate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    issue = service.get(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check permissions (Developer must be assignee)
    user_roles = [r.name for r in user.roles]
    if "Developer" in user_roles and "Admin" not in user_roles and "Project Manager" not in user_roles:
        if issue.assigned_to != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this issue status")

    old_status = issue.status_id
    old_root_cause = issue.root_cause
    old_resolution = issue.resolution

    issue.status_id = data.status_id
    if data.root_cause is not None:
        issue.root_cause = data.root_cause.strip() if isinstance(data.root_cause, str) else data.root_cause
    if data.resolution is not None:
        issue.resolution = data.resolution.strip() if isinstance(data.resolution, str) else data.resolution

    if data.comment and data.comment.strip():
        from app.models.comment import IssueComment
        comment_obj = IssueComment(
            issue_id=issue.id,
            user_id=user.id,
            content=data.comment.strip()
        )
        db.add(comment_obj)

    db.commit()
    db.refresh(issue)

    # Track history
    from types import SimpleNamespace
    old_mock = SimpleNamespace(
        id=issue.id,
        issue_key=issue.issue_key,
        title=issue.title,
        description=issue.description,
        issue_type=issue.issue_type,
        status_id=old_status,
        priority_id=issue.priority_id,
        severity_id=issue.severity_id,
        category_id=issue.category_id,
        module_id=issue.module_id,
        environment=issue.environment,
        browser=issue.browser,
        operating_system=issue.operating_system,
        reproduction_steps=issue.reproduction_steps,
        expected_behavior=issue.expected_behavior,
        actual_behavior=issue.actual_behavior,
        root_cause=old_root_cause,
        resolution=old_resolution,
        attachment_path=issue.attachment_path,
        sprint_id=issue.sprint_id,
        project_id=issue.project_id,
        reporter_id=issue.reporter_id,
        assigned_to=issue.assigned_to,
        embedding_vector=issue.embedding_vector,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        is_active=issue.is_active,
        is_deleted=issue.is_deleted
    )
    service.track_issue_changes(db, old_mock, issue, user.id)

    return serialize(issue)


class IssueAssignUpdate(BaseModel):
    assigned_to: int | None = None


@router.patch("/{issue_id}/assign", response_model=IssueResponse)
async def update_issue_assignee(
    issue_id: int,
    data: IssueAssignUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """
    Immediately persist assignee changes to the database.
    """
    from app.repositories.user_repository import UserRepository

    issue = service.get(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    user_roles = [r.name for r in user.roles]
    can_assign = any(
        r in ["Admin", "Project Manager", "Team Leader", "PM", "TL", "QA"] for r in user_roles
    )
    if not can_assign:
        raise HTTPException(status_code=403, detail="Not authorized to reassign this issue")

    if data.assigned_to is not None and data.assigned_to > 0:
        assignee_user = UserRepository().get_by_id(db, data.assigned_to)
        if not assignee_user:
            raise HTTPException(status_code=422, detail="Selected assignee does not exist")

    old_assigned_to = issue.assigned_to
    issue.assigned_to = data.assigned_to if (data.assigned_to and data.assigned_to > 0) else None

    db.commit()
    db.refresh(issue)

    # Track history
    from types import SimpleNamespace
    old_mock = SimpleNamespace(
        id=issue.id,
        issue_key=issue.issue_key,
        title=issue.title,
        description=issue.description,
        issue_type=issue.issue_type,
        status_id=issue.status_id,
        priority_id=issue.priority_id,
        severity_id=issue.severity_id,
        category_id=issue.category_id,
        module_id=issue.module_id,
        environment=issue.environment,
        browser=issue.browser,
        operating_system=issue.operating_system,
        reproduction_steps=issue.reproduction_steps,
        expected_behavior=issue.expected_behavior,
        actual_behavior=issue.actual_behavior,
        root_cause=issue.root_cause,
        resolution=issue.resolution,
        attachment_path=issue.attachment_path,
        sprint_id=issue.sprint_id,
        project_id=issue.project_id,
        reporter_id=issue.reporter_id,
        assigned_to=old_assigned_to,
        embedding_vector=issue.embedding_vector,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        is_active=issue.is_active,
        is_deleted=issue.is_deleted
    )
    service.track_issue_changes(db, old_mock, issue, user.id)

    return serialize(issue)


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)



async def delete_issue(issue_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    user_roles = [r.name for r in user.roles]
    if not any(role in user_roles for role in ["Admin", "Project Manager"]):
        raise HTTPException(status_code=403, detail="Not authorized to delete defects")
    service.delete(db, issue_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Similar Issues Endpoint ──

@router.get("/{issue_id}/similar", response_model=list[SimilarIssueResponse])
async def get_similar_issues(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    project_id: int | None = Query(default=None, description="Optional: limit to specific project"),
):
    """
    Find issues similar to an existing issue using semantic embedding similarity.
    Results are filtered by project and sorted by similarity score.
    """
    try:
        return service.find_similar_issues(db, issue_id, project_id=project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar issues lookup failed: {e}")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Similar issue detection temporarily unavailable")


# ── History & Comments ──

def serialize_history(h):
    return {
        "id": h.id,
        "issue_id": h.issue_id,
        "user_id": h.user_id,
        "user_name": h.user.full_name if getattr(h, 'user', None) else "System",
        "field_name": h.field_name,
        "old_value": h.old_value,
        "new_value": h.new_value,
        "created_at": h.created_at
    }

def serialize_comment(c):
    return {
        "id": c.id,
        "issue_id": c.issue_id,
        "user_id": c.user_id,
        "user_name": c.user.full_name if c.user is not None else "Unknown",
        "content": c.content,
        "created_at": c.created_at,
        "updated_at": getattr(c, 'updated_at', None)
    }

@router.get("/{issue_id}/history", response_model=list[IssueHistoryResponse])
async def get_issue_history(issue_id: int, db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    return [serialize_history(h) for h in service.get_history(db, issue_id)]

@router.get("/{issue_id}/comments", response_model=list[IssueCommentResponse])
async def get_issue_comments(issue_id: int, db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    return [serialize_comment(c) for c in service.get_comments(db, issue_id)]

@router.post("/{issue_id}/comments", response_model=IssueCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_issue_comment(issue_id: int, data: IssueCommentCreate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    try:
        comment = service.create_comment(db, issue_id, data.content, user)
        return serialize_comment(comment)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Attachments ──

def serialize_attachment(a):
    return {
        "id": a.id,
        "issue_id": a.issue_id,
        "filename": a.filename,
        "file_path": a.file_path,
        "file_size": a.file_size,
        "mime_type": a.mime_type,
        "uploaded_by": a.uploaded_by,
        "uploader_name": a.uploader.full_name if getattr(a, 'uploader', None) else None,
        "created_at": a.created_at,
    }


@router.get("/{issue_id}/attachments", )
async def get_issue_attachments(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return [serialize_attachment(a) for a in service.get_attachments(db, issue_id)]


@router.post("/{issue_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_issue_attachment(
    issue_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    import os, uuid, shutil
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(uploads_dir, unique_name)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    file_size = os.path.getsize(dest)
    att = service.add_attachment(
        db, issue_id,
        filename=file.filename or unique_name,
        file_path=f"/{dest}",
        file_size=file_size,
        mime_type=file.content_type,
        user=user,
    )
    return serialize_attachment(att)


@router.delete("/{issue_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)


async def delete_issue_attachment(
    issue_id: int,
    attachment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service.delete_attachment(db, issue_id, attachment_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

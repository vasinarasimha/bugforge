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
    IssueAssignTeamRequest, IssueQAVerifyRequest, FeatureRequestSubmit,
)
from app.schemas.attachment import IssueAttachmentResponse
from app.services.issue_service import IssueService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["Issues"])
service = IssueService()

def serialize(i, current_user=None):
    user_company = getattr(current_user, 'company_id', None) if current_user else None
    user_roles = [r.name for r in getattr(current_user, 'roles', [])] if current_user else []
    is_super_admin = "Super Admin" in user_roles

    hide_internal_details = (
        not is_super_admin
        and user_company is not None
        and getattr(i, 'requesting_company_id', None) == user_company
        and i.company_id != user_company
    )

    assigned_to = None if hide_internal_details else i.assigned_to
    assignee_name = ("BugForge Engineering Team" if i.assigned_to else None) if hide_internal_details else (i.assignee.full_name if getattr(i, 'assignee', None) else None)

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
        "assigned_to": assigned_to,
        "assignee": assignee_name,
        "company_id": i.company_id,
        "requesting_company_id": getattr(i, 'requesting_company_id', None),
        "requesting_company_name": i.requesting_company.name if getattr(i, 'requesting_company', None) else None,
        "team_id": getattr(i, 'team_id', None),
        "team_name": i.team.name if getattr(i, 'team', None) else None,
        "qa_state": getattr(i, 'qa_state', None),
        "qa_verified_by_id": None if hide_internal_details else getattr(i, 'qa_verified_by_id', None),
        "qa_verified_by_name": ("BugForge QA Team" if getattr(i, 'qa_verified_by_id', None) else None) if hide_internal_details else (i.qa_verified_by.full_name if getattr(i, 'qa_verified_by', None) else None),
        "qa_verified_at": getattr(i, 'qa_verified_at', None),
        "ai_root_cause_session_id": getattr(i, 'ai_root_cause_session_id', None),
        "created_at": i.created_at,
        "updated_at": i.updated_at,
        "is_active": i.is_active
    }

@router.get("/statuses", response_model=list[IssueStatusResponse])
async def list_statuses(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.company_id:
        company_statuses = db.query(IssueStatus).filter(
            IssueStatus.company_id == current_user.company_id,
            IssueStatus.is_active == True
        ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()
        if company_statuses:
            return company_statuses
    global_statuses = db.query(IssueStatus).filter(
        IssueStatus.is_active == True,
        IssueStatus.company_id == None
    ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()
    if global_statuses:
        return global_statuses
    return db.query(IssueStatus).filter(
        IssueStatus.is_active == True,
        IssueStatus.company_id == 1
    ).order_by(IssueStatus.order_index.asc(), IssueStatus.id.asc()).all()

@router.get("/priorities", response_model=list[IssuePriorityResponse])
async def list_priorities(db: Annotated[Session, Depends(get_db)]):
    return db.query(IssuePriority).filter(IssuePriority.is_active == True).all()

@router.get("/severities", response_model=list[IssueSeverityResponse])
async def list_severities(db: Annotated[Session, Depends(get_db)]):
    return db.query(IssueSeverity).filter(IssueSeverity.is_active == True).all()

@router.get("/categories", response_model=list[IssueCategoryResponse])
async def list_categories(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    query = db.query(IssueCategory).filter(IssueCategory.is_active == True)
    if current_user.company_id:
        query = query.filter((IssueCategory.company_id == current_user.company_id) | (IssueCategory.company_id == None))
    return query.all()

@router.get("/modules", response_model=list[IssueModuleResponse])
async def list_modules(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    query = db.query(IssueModule).filter(IssueModule.is_active == True)
    if current_user.company_id:
        query = query.filter((IssueModule.company_id == current_user.company_id) | (IssueModule.company_id == None))
    return query.all()


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
            db, query=data.query, project_id=data.project_id, limit=data.limit, company_id=user.company_id
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
            project_id=search_request.project_id,
            company_id=user.company_id,
        )
        # Return in backward-compatible format: [{issue: {...}, similarity: float}]
        return [{"issue": serialize(service.get(db, r["id"], company_id=user.company_id)), "similarity": r["similarity_score"]} for r in results]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Search temporarily unavailable")


# ── CRUD Endpoints ──

@router.get("", response_model=list[IssueResponse])
async def list_issues(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    issue_type: str | None = Query(default=None),
    requesting_company_id: int | None = Query(default=None),
):
    user_roles = [r.name for r in user.roles]
    reporter_id = user.id if "Reporter" in user_roles and "Admin" not in user_roles and "Project Manager" not in user_roles and "Team Leader" not in user_roles and "QA" not in user_roles else None

    # Customer security check: Non-Super Admin cannot query other company's feature requests
    effective_req_company = requesting_company_id
    if "Super Admin" not in user_roles and requesting_company_id and requesting_company_id != user.company_id:
        raise HTTPException(status_code=403, detail="Cannot view feature requests of another company")

    issues = service.repository.list(
        db,
        reporter_id=reporter_id,
        company_id=user.company_id,
        issue_type=issue_type,
        requesting_company_id=effective_req_company,
    )
    return [serialize(i, user) for i in issues]

@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    return serialize(service.get(db, issue_id, company_id=user.company_id), user)

@router.post("/feature-requests", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def submit_feature_request(
    data: FeatureRequestSubmit,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Customer Company Admin submits a Feature Request to BugForge.
    Creates an internal Issue of type 'Feature' with requesting_company_id.
    """
    user_roles = [r.name for r in current_user.roles]
    if "Admin" not in user_roles and "Super Admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Only Company Admins can submit feature requests")

    created = service.submit_feature_request(
        db=db,
        title=data.title,
        description=data.description,
        user=current_user,
        priority_id=data.priority_id,
        severity_id=data.severity_id,
    )
    return serialize(created, current_user)

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
                company_id=user.company_id,
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
    issue = service.get(db, issue_id, company_id=user.company_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    target_status = db.query(IssueStatus).filter(IssueStatus.id == data.status_id).first()
    if not target_status:
        raise HTTPException(status_code=404, detail="Status not found")
    if user.company_id and target_status.company_id and target_status.company_id != user.company_id:
        raise HTTPException(status_code=403, detail="Unauthorized status selection")
    if not target_status.is_active:
        raise HTTPException(status_code=422, detail="Selected status is inactive")

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

    # Send notifications on workflow status changes
    service.notify_status_change(db, issue, old_status, data.status_id, user)

    return serialize(issue, user)


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
    Assign issue to developer. Authorized for Super Admin, Admin, and PM/TL of the assigned team.
    """
    updated = service.assign_developer(db, issue_id, data.assigned_to, user)
    return serialize(updated, user)


@router.patch("/{issue_id}/assign-team", response_model=IssueResponse)
async def assign_issue_team(
    issue_id: int,
    data: IssueAssignTeamRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """
    Super Admin assigns a feature issue to an internal BugForge team.
    """
    updated = service.assign_team(db, issue_id, data.team_id, user)
    return serialize(updated, user)


@router.patch("/{issue_id}/qa-verify", response_model=IssueResponse)
async def qa_verify_issue(
    issue_id: int,
    data: IssueQAVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """
    QA verifies the feature implementation: Passed or Requires Rework.
    """
    updated = service.qa_verify(db, issue_id, data.qa_state, data.notes, user)
    return serialize(updated, user)


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
        return service.find_similar_issues(db, issue_id, project_id=project_id, company_id=user.company_id)
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
        import logging
        logging.getLogger(__name__).error(f"Failed to create comment on issue {issue_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create comment. Please try again.")


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

    # File size validation (10MB max)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB."
        )
    await file.seek(0)

    # MIME type validation
    ALLOWED_MIME_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
        "application/pdf",
        "text/plain", "text/csv", "text/markdown",
        "application/json",
        "application/zip", "application/x-zip-compressed",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "video/mp4", "video/webm",
    }
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' is not allowed."
        )

    # Sanitize filename — strip path components to prevent path traversal
    raw_name = file.filename or "attachment"
    safe_basename = os.path.basename(raw_name).lstrip(".")
    if not safe_basename:
        safe_basename = "attachment"
    ext = os.path.splitext(safe_basename)[1]

    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(uploads_dir, unique_name)
    with open(dest, "wb") as f:
        f.write(contents)
    file_size = os.path.getsize(dest)
    att = service.add_attachment(
        db, issue_id,
        filename=safe_basename,
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

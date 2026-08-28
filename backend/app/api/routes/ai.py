from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.issue import Issue, IssueStatus
from app.models.comment import IssueComment
from app.repositories.issue_repository import IssueRepository
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service

router = APIRouter(prefix="/ai")

class FormatIssueRequest(BaseModel):
    title: str
    description: str

class ResolutionAssistanceRequest(BaseModel):
    issue_id: int

@router.post("/format-issue")
async def format_issue(req: FormatIssueRequest, _: Annotated[User, Depends(get_current_user)]):
    return llm_service.format_issue(req.title, req.description)

@router.post("/resolution-assistance")
async def get_resolution_assistance(
    req: ResolutionAssistanceRequest,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # Fetch the issue
    issue_repo = IssueRepository()
    issue = issue_repo.get(db, req.issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Ensure we have an embedding
    embedding = issue.embedding_vector
    if embedding is None:
        category_name = issue.category.name if getattr(issue, 'category', None) else None
        module_name = issue.module.name if getattr(issue, 'module', None) else None
        embedding = embedding_service.embed_issue(
            title=issue.title,
            description=issue.description,
            category=category_name,
            module=module_name,
            issue_type=issue.issue_type
        )
        if embedding is not None:
            issue.embedding_vector = embedding
            db.commit()

    if not embedding:
        # Fallback if embedding is totally unavailable
        similar_issues = []
    else:
        # Find resolved/closed statuses
        terminal_statuses = db.query(IssueStatus).filter(
            (IssueStatus.name.ilike('%resolved%')) | (IssueStatus.name.ilike('%closed%')),
            IssueStatus.is_active == True
        ).all()
        status_ids = [s.id for s in terminal_statuses]
        
        # Semantic search for similar resolved defects
        similar_tuples = []
        if status_ids:
            similar_tuples = issue_repo.find_similar(
                db=db,
                embedding=embedding,
                exclude_issue_id=issue.id,
                project_id=issue.project_id,
                status_ids=status_ids,
                similarity_threshold=0.60,
                limit=5
            )
        similar_issues = [
            {"issue": sim_issue, "similarity": sim_score} for sim_issue, sim_score in similar_tuples
        ]

    def issue_to_dict(issue_obj: Issue) -> dict:
        return {
            "issue_key": issue_obj.issue_key,
            "title": issue_obj.title,
            "description": issue_obj.description,
            "severity_name": issue_obj.severity.name if issue_obj.severity else "Unknown",
            "priority_name": issue_obj.priority.name if issue_obj.priority else "Unknown",
        }

    def similar_issue_to_dict(item: dict) -> dict:
        issue_obj = item["issue"]
        similarity = item["similarity"]
        
        # Fetch comments
        comments = db.query(IssueComment).filter(
            IssueComment.issue_id == issue_obj.id,
            IssueComment.is_deleted == False
        ).order_by(IssueComment.created_at.desc()).limit(3).all()
        
        return {
            "defect_id": issue_obj.issue_key or str(issue_obj.id),
            "title": issue_obj.title,
            "description": issue_obj.description,
            "status_name": issue_obj.status.name if issue_obj.status else "Unknown",
            "similarity_score": round(similarity, 2),
            "root_cause": getattr(issue_obj, "root_cause", None),
            "resolution": getattr(issue_obj, "resolution", None),
            "relevant_comments": [c.content for c in comments]
        }

    issue_dict = issue_to_dict(issue)
    similar_resolved_list = [similar_issue_to_dict(item) for item in similar_issues]

    # Generate resolution assistance
    result = llm_service.generate_resolution_assistance(issue_dict, similar_resolved_list)
    return result
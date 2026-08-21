from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.issue import Issue, IssueStatus
from app.repositories.issue_repository import IssueRepository
from app.services.llm_service import llm_service

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

    # Find resolved status (case-insensitive match for 'resolved' or 'closed')
    resolved_status = db.query(IssueStatus).filter(
        IssueStatus.name.ilike('%resolved%'),
        IssueStatus.is_active == True
    ).first()
    if not resolved_status:
        resolved_status = db.query(IssueStatus).filter(
            IssueStatus.name.ilike('%closed%'),
            IssueStatus.is_active == True
        ).first()

    # Fetch recent similar resolved issues from the same project (excluding current issue)
    similar_resolved = []
    if resolved_status:
        similar_resolved = db.query(Issue).filter(
            Issue.project_id == issue.project_id,
            Issue.status_id == resolved_status.id,
            Issue.id != issue.id,
            Issue.is_deleted == False,
            Issue.is_active == True
        ).order_by(Issue.created_at.desc()).limit(5).all()

    # Helper to convert Issue to dict for LLM service
    def issue_to_dict(issue_obj: Issue) -> dict:
        return {
            "issue_key": issue_obj.issue_key,
            "title": issue_obj.title,
            "description": issue_obj.description,
            "severity_name": issue_obj.severity.name if issue_obj.severity else "Unknown",
            "priority_name": issue_obj.priority.name if issue_obj.priority else "Unknown",
        }

    def similar_issue_to_dict(issue_obj: Issue) -> dict:
        return {
            "issue_key": issue_obj.issue_key,
            "title": issue_obj.title,
            "description": issue_obj.description,
            "status_name": issue_obj.status.name if issue_obj.status else "Unknown",
        }

    issue_dict = issue_to_dict(issue)
    similar_resolved_list = [similar_issue_to_dict(i) for i in similar_resolved]

    # Generate resolution assistance
    result = llm_service.generate_resolution_assistance(issue_dict, similar_resolved_list)
    return result
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role, get_effective_company_id
from app.core.database import get_db
from app.models.user import User
from app.models.issue import Issue, IssueStatus
from app.models.comment import IssueComment
from app.models.troubleshooting import TroubleshootingSession
from app.repositories.issue_repository import IssueRepository
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service
from app.api.routes.troubleshooting import router as troubleshooting_router
from app.schemas.qa import (
    GenerateTestCasesRequest,
    TestCaseGenerationResponse,
    MissingScenariosRequest,
    MissingScenariosResponse,
)

router = APIRouter(prefix="/ai")
router.include_router(troubleshooting_router)

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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    cid = get_effective_company_id(current_user)
    # Fetch the issue
    issue_repo = IssueRepository()
    issue = issue_repo.get(db, req.issue_id, company_id=cid)
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
                limit=5,
                company_id=cid,
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
    try:
        result = llm_service.generate_resolution_assistance(issue_dict, similar_resolved_list)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to generate resolution assistance: {e}")
        result = {
            "historical_resolutions": [],
            "investigation_areas": ["Review application logs", "Check recent code changes"],
            "possible_causes": ["Unexpected application error"],
            "suggested_resolution": "Review relevant logs and recent code changes.",
            "similar_defects_summary": "AI resolution assistance is temporarily unavailable."
        }

    # Enhance with AI root-cause analysis data if available
    ai_root_cause = None
    if getattr(issue, 'ai_root_cause_session_id', None):
        try:
            ts = db.query(TroubleshootingSession).filter(
                TroubleshootingSession.id == issue.ai_root_cause_session_id
            ).first()
            if ts and ts.root_cause:
                ai_root_cause = {
                    "root_cause": ts.root_cause,
                    "confidence": ts.confidence,
                    "evidence": ts.evidence_summary or [],
                    "recommended_fix": ts.recommended_fix,
                    "status": ts.status,
                }
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to fetch AI root cause session: {e}")

    result["ai_root_cause"] = ai_root_cause
    return result


def _build_defect_context(db: Session, issue: Issue) -> dict:
    """Helper to extract comprehensive defect context for QA AI prompts."""
    ai_root_cause = None
    if getattr(issue, 'ai_root_cause_session_id', None):
        try:
            ts = db.query(TroubleshootingSession).filter(
                TroubleshootingSession.id == issue.ai_root_cause_session_id
            ).first()
            if ts and ts.root_cause:
                ai_root_cause = ts.root_cause
        except Exception:
            pass

    return {
        "id": issue.id,
        "issue_key": issue.issue_key,
        "title": issue.title,
        "description": issue.description,
        "reproduction_steps": issue.reproduction_steps,
        "expected_behavior": issue.expected_behavior,
        "actual_behavior": issue.actual_behavior,
        "severity_name": issue.severity.name if issue.severity else "Unknown",
        "priority_name": issue.priority.name if issue.priority else "Unknown",
        "status_name": issue.status.name if issue.status else "Unknown",
        "category_name": issue.category.name if getattr(issue, 'category', None) else "General",
        "module_name": issue.module.name if getattr(issue, 'module', None) else "General",
        "project_name": issue.project.name if getattr(issue, 'project', None) else "General",
        "environment": issue.environment,
        "browser": issue.browser,
        "operating_system": issue.operating_system,
        "root_cause": getattr(issue, 'root_cause', None),
        "resolution": getattr(issue, 'resolution', None),
        "ai_root_cause": ai_root_cause,
    }


QA_ALLOWED_ROLES = ["Admin", "Project Manager", "Team Leader", "QA", "PM", "TL"]


@router.post("/test-cases", response_model=TestCaseGenerationResponse)
async def generate_test_cases(
    req: GenerateTestCasesRequest,
    current_user: Annotated[User, Depends(require_role(QA_ALLOWED_ROLES))],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Generate structured, multi-perspective QA test cases for an existing defect.
    Restricted to Admin, PM, TL, and QA roles.
    """
    cid = get_effective_company_id(current_user)
    issue_repo = IssueRepository()
    issue = issue_repo.get(db, req.issue_id, company_id=cid)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    defect_context = _build_defect_context(db, issue)
    return llm_service.generate_test_cases(defect_context)


@router.post("/missing-scenarios", response_model=MissingScenariosResponse)
async def detect_missing_scenarios(
    req: MissingScenariosRequest,
    current_user: Annotated[User, Depends(require_role(QA_ALLOWED_ROLES))],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Analyze defect and existing test cases to identify overlooked edge cases and test coverage gaps.
    Restricted to Admin, PM, TL, and QA roles.
    """
    cid = get_effective_company_id(current_user)
    issue_repo = IssueRepository()
    issue = issue_repo.get(db, req.issue_id, company_id=cid)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    defect_context = _build_defect_context(db, issue)
    return llm_service.detect_missing_scenarios(defect_context, req.existing_test_cases)
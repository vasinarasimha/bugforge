from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.services.llm_service import GroqService

router = APIRouter(prefix="/ai", tags=["AI"])
llm_service = GroqService()

class FormatIssueRequest(BaseModel):
    title: str
    description: str

class TimelineRequest(BaseModel):
    recent_issues: list[dict]

@router.post("/format-issue")
async def format_issue(req: FormatIssueRequest, _: Annotated[User, Depends(get_current_user)]):
    return llm_service.format_issue(req.title, req.description)

@router.post("/summarize-timeline")
async def summarize_timeline(req: TimelineRequest, _: Annotated[User, Depends(get_current_user)]):
    return llm_service.summarize_timeline(req.recent_issues)

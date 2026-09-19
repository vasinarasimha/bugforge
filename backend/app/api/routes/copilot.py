"""
AI Copilot API Route.

Provides the POST /api/ai/copilot/chat endpoint for the frontend
Copilot drawer. Fully isolated from existing AI routes.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, get_effective_company_id
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/ai/copilot")
alt_router = APIRouter(prefix="/copilot")


class CopilotChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message to the AI Copilot")
    conversation_history: list[dict] | None = Field(
        None,
        description="Optional previous messages for multi-turn context",
        max_length=10,
    )


class CopilotChatResponse(BaseModel):
    reply: str
    tools_used: list[str] = []
    error: str | None = None


@router.post("/chat", response_model=CopilotChatResponse)
@alt_router.post("/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    req: CopilotChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Send a message to the AI Copilot. The copilot can invoke read-only
    tools to query BugForge data (issues, analytics, projects, sprints)
    scoped to the user's tenant.
    """
    # Lazy import to avoid circular dependencies at module load time
    from app.services.copilot_service import copilot_service

    company_id = get_effective_company_id(current_user)

    result = copilot_service.chat(
        message=req.message,
        db=db,
        current_user=current_user,
        company_id=company_id,
        conversation_history=req.conversation_history,
    )

    return CopilotChatResponse(**result)

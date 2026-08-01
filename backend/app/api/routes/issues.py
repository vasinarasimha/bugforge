from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.issue import IssueCreate, IssueResponse, IssueUpdate
from app.services.issue_service import IssueService

router = APIRouter(prefix="/issues", tags=["Issues"])
service = IssueService()
def serialize(i): return {"id":i.id,"title":i.title,"description":i.description,"status":i.status,"priority":i.priority,"project_id":i.project_id,"project_name":i.project.project_name,"reporter_id":i.reporter_id,"reporter_name":i.reporter.full_name,"assigned_to":i.assigned_to,"created_at":i.created_at,"updated_at":i.updated_at}

@router.get("", response_model=list[IssueResponse])
async def list_issues(db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]): return [serialize(i) for i in service.list(db)]
@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: int, db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]): return serialize(service.get(db, issue_id))
@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(data: IssueCreate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]): return serialize(service.create(db, data, user))
@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(issue_id: int, data: IssueUpdate, db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]): return serialize(service.update(db, issue_id, data))
@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(issue_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    if user.role not in ["Admin", "QA"]: raise HTTPException(status_code=403, detail="Not authorized to delete issues")
    service.delete(db, issue_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])
service = ProjectService()
def serialize(p): return {"id":p.id,"project_name":p.project_name,"description":p.description,"created_by":p.created_by,"created_by_name":p.creator.full_name,"created_at":p.created_at,"updated_at":p.updated_at,"issue_count":len(p.issues)}

@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]): return [serialize(p) for p in service.list(db)]
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]): return serialize(service.get(db, project_id))
@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    if user.role != "Admin": raise HTTPException(status_code=403, detail="Not authorized to create projects")
    return serialize(service.create(db, data, user))
@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, data: ProjectUpdate, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    if user.role != "Admin": raise HTTPException(status_code=403, detail="Not authorized to update projects")
    return serialize(service.update(db, project_id, data))
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    if user.role != "Admin": raise HTTPException(status_code=403, detail="Not authorized to delete projects")
    service.delete(db, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self):
        self.repository = ProjectRepository()

    def list(self, db: Session):
        # print("services/project_service.py Fetching all projects")
        return self.repository.list(db)
    def get(self, db: Session, project_id: int):
        # print(f"services/project_service.py Fetching project with ID {project_id}")
        project = self.repository.get(db, project_id)
        if not project:
            # print("services/project_service.py Project not found")
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        return project
    def create(self, db: Session, data: ProjectCreate, user: User):
        # print(f"services/project_service.py Creating project with name: {data.project_name}")
        return self.repository.create(db, Project(project_name=data.project_name.strip(), description=data.description.strip(), created_by=user.id))
    def update(self, db: Session, project_id: int, data: ProjectUpdate):
        # print(f"services/project_service.py Updating project with ID {project_id}")
        project = self.get(db, project_id)
        project.project_name, project.description = data.project_name.strip(), data.description.strip()
        db.commit(); db.refresh(project)
        return self.repository.get(db, project.id)
    def delete(self, db: Session, project_id: int):
        # print(f"services/project_service.py Deleting project with ID {project_id}")
        self.repository.delete(db, self.get(db, project_id))

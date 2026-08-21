from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    def __init__(self):
        self.repository = ProjectRepository()

    def list(self, db: Session, **kwargs):
        print("services/project_service.py Fetching all projects")
        return self.repository.list(db)
        
    def list_by_manager(self, db: Session, manager_id: int, **kwargs):
        return self.repository.list(db)
        
    def list_by_leader(self, db: Session, leader_id: int, **kwargs):
        return self.repository.list(db)

    def get(self, db: Session, project_id: int):
        print(f"services/project_service.py Fetching project with ID {project_id}")
        project = self.repository.get(db, project_id)
        if not project:
            print("services/project_service.py Project not found")
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        return project

    def create(self, db: Session, data: ProjectCreate, user: User):
        print(f"services/project_service.py Creating project with name: {data.name}")
        project = Project(
            name=data.name.strip(),
            key=data.key.strip().upper(),
            description=data.description.strip() if data.description else "",
            repository_url=data.repository_url,
            status=data.status,
            client_name=data.client_name,
            start_date=data.start_date,
            end_date=data.end_date,
            budget=data.budget,
            tech_stack=data.tech_stack,
            project_manager_id=data.project_manager_id,
            team_leader_id=data.team_leader_id,
            created_by=user.id
        )
        return self.repository.create(db, project)

    def update(self, db: Session, project_id: int, data: ProjectUpdate, user: User):
        print(f"services/project_service.py Updating project with ID {project_id}")
        project = self.get(db, project_id)
        
        project.name = data.name.strip()
        project.key = data.key.strip().upper()
        project.description = data.description.strip() if data.description else ""
        project.repository_url = data.repository_url
        project.status = data.status
        project.client_name = data.client_name
        project.start_date = data.start_date
        project.end_date = data.end_date
        project.budget = data.budget
        project.tech_stack = data.tech_stack
        project.project_manager_id = data.project_manager_id
        project.team_leader_id = data.team_leader_id
        
        db.commit()
        db.refresh(project)
        return self.repository.get(db, project.id)

    def delete(self, db: Session, project_id: int):
        print(f"services/project_service.py Deleting project with ID {project_id}")
        project = self.get(db, project_id)
        
        # Cascade soft-delete to issues
        from app.repositories.issue_repository import IssueRepository
        issue_repo = IssueRepository()
        for issue in project.issues:
            issue.is_deleted = True
        
        self.repository.delete(db, project)


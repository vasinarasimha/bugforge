from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_effective_company_id, is_super_admin
from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    def __init__(self):
        self.repository = ProjectRepository()

    def list(self, db: Session, company_id: int | None = None, **kwargs):
        print("services/project_service.py Fetching all projects")
        return self.repository.list(db, company_id=company_id, **kwargs)
        
    def list_by_manager(self, db: Session, manager_id: int, company_id: int | None = None, **kwargs):
        return self.repository.list_by_manager(db, manager_id, company_id=company_id, **kwargs)
        
    def list_by_leader(self, db: Session, leader_id: int, company_id: int | None = None, **kwargs):
        return self.repository.list_by_leader(db, leader_id, company_id=company_id, **kwargs)

    def get(self, db: Session, project_id: int, company_id: int | None = None):
        print(f"services/project_service.py Fetching project with ID {project_id}")
        project = self.repository.get(db, project_id, company_id=company_id)
        if not project:
            print("services/project_service.py Project not found")
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        return project

    def _validate_members(self, db: Session, pm_id: int | None, tl_id: int | None, company_id: int | None):
        if company_id is None:
            return
        if pm_id:
            pm = db.query(User).filter(User.id == pm_id).first()
            if not pm:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Project manager does not exist")
            if getattr(pm, 'company_id', None) != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign project manager from another company")
        if tl_id:
            tl = db.query(User).filter(User.id == tl_id).first()
            if not tl:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Team leader does not exist")
            if getattr(tl, 'company_id', None) != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign team leader from another company")

    def create(self, db: Session, data: ProjectCreate, user: User):
        print(f"services/project_service.py Creating project with name: {data.name}")
        is_super = is_super_admin(user)
        company_id = getattr(data, 'company_id', None) if is_super else (user.company_id or 1)
        if not company_id:
            company_id = user.company_id or 1

        team = None
        if data.team_id:
            from app.models.team import Team
            team = db.query(Team).filter(Team.id == data.team_id).first()
            if not team:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected team does not exist")
            if company_id is not None and team.company_id != company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign team from another company")

        project_manager_id = (team.project_manager_id if team else None) or data.project_manager_id
        team_leader_id = (team.team_leader_id if team else None) or data.team_leader_id
        self._validate_members(db, project_manager_id, team_leader_id, company_id)

        # Check duplicate key or name in this company
        existing_proj = db.query(Project).filter(
            Project.company_id == company_id,
            or_(
                func.lower(Project.name) == data.name.strip().lower(),
                func.upper(Project.key) == data.key.strip().upper(),
            )
        ).first()
        if existing_proj:
            if existing_proj.key.upper() == data.key.strip().upper():
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"A project with key '{data.key.strip().upper()}' already exists in this company."
                )
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"A project with name '{data.name.strip()}' already exists in this company."
            )

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
            team_id=data.team_id,
            project_manager_id=project_manager_id,
            team_leader_id=team_leader_id,
            company_id=company_id,
            created_by=user.id
        )
        return self.repository.create(db, project)

    def update(self, db: Session, project_id: int, data: ProjectUpdate, user: User):
        print(f"services/project_service.py Updating project with ID {project_id}")
        effective_cid = get_effective_company_id(user)
        project = self.get(db, project_id, company_id=effective_cid)

        team = None
        if data.team_id:
            from app.models.team import Team
            team = db.query(Team).filter(Team.id == data.team_id).first()
            if not team:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected team does not exist")
            if project.company_id is not None and team.company_id != project.company_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign team from another company")

        project_manager_id = (team.project_manager_id if team else None) or data.project_manager_id
        team_leader_id = (team.team_leader_id if team else None) or data.team_leader_id
        self._validate_members(db, project_manager_id, team_leader_id, project.company_id)
        
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
        project.team_id = data.team_id
        project.project_manager_id = project_manager_id
        project.team_leader_id = team_leader_id
        
        db.commit()
        db.refresh(project)
        return self.repository.get(db, project.id, company_id=effective_cid)

    def delete(self, db: Session, project_id: int, user: User | None = None):
        print(f"services/project_service.py Deleting project with ID {project_id}")
        effective_cid = get_effective_company_id(user) if user else None
        project = self.get(db, project_id, company_id=effective_cid)
        
        # Cascade soft-delete to issues
        for issue in project.issues:
            issue.is_deleted = True
        
        self.repository.delete(db, project)


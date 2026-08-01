from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project


class ProjectRepository:
    def list(self, db: Session) -> list[Project]:
        # print("repositories/project_repository.py Fetching all projects from the database")
        return list(db.scalars(select(Project).options(selectinload(Project.creator), selectinload(Project.issues)).order_by(Project.created_at.desc())))

    def get(self, db: Session, project_id: int) -> Project | None:
        # print(f"repositories/project_repository.py Fetching project with ID {project_id} from the database")
        return db.scalar(select(Project).options(selectinload(Project.creator), selectinload(Project.issues)).where(Project.id == project_id))

    def create(self, db: Session, project: Project) -> Project:
        # print(f"repositories/project_repository.py Creating a new project with name '{project.name}' in the database")
        db.add(project); db.commit(); db.refresh(project)
        return self.get(db, project.id)  # type: ignore[return-value]

    def delete(self, db: Session, project: Project) -> None:
        # print(f"repositories/project_repository.py Deleting project with ID {project.id} from the database")
        db.delete(project); db.commit()

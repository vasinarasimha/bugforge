from sqlalchemy import select

from sqlalchemy.orm import Session, selectinload



from app.models.project import Project





class ProjectRepository:

    def list(self, db: Session, search: str | None = None, limit: int | None = None, offset: int | None = None) -> list:

        print("repositories/project_repository.py Fetching all projects from the database")

        query = select(Project).options(selectinload(Project.creator), selectinload(Project.issues)).where(Project.is_active == True)

        if search:

            query = query.where(Project.name.ilike(f"%{search}%"))

        query = query.order_by(Project.created_at.desc())

        if limit is not None:

            query = query.limit(limit)

        if offset is not None:

            query = query.offset(offset)

        return list(db.scalars(query))



    def list_by_manager(self, db: Session, manager_id: int, search: str | None = None, limit: int | None = None, offset: int | None = None) -> list:

        print(f"repositories/project_repository.py Fetching projects for manager ID: {manager_id} from the database")

        query = select(Project).options(selectinload(Project.creator), selectinload(Project.issues)).where(Project.project_manager_id == manager_id, Project.is_active == True)

        if search:

            query = query.where(Project.name.ilike(f"%{search}%"))

        query = query.order_by(Project.created_at.desc())

        if limit is not None:

            query = query.limit(limit)

        if offset is not None:

            query = query.offset(offset)

        return list(db.scalars(query))



    def list_by_leader(self, db: Session, leader_id: int, search: str | None = None, limit: int | None = None, offset: int | None = None) -> list:

        print(f"repositories/project_repository.py Fetching projects for leader ID: {leader_id} from the database")

        query = select(Project).options(selectinload(Project.creator), selectinload(Project.issues)).where(Project.team_leader_id == leader_id, Project.is_active == True)

        if search:

            query = query.where(Project.name.ilike(f"%{search}%"))

        query = query.order_by(Project.created_at.desc())

        if limit is not None:

            query = query.limit(limit)

        if offset is not None:

            query = query.offset(offset)

        return list(db.scalars(query))



    def get(self, db: Session, project_id: int) -> Project | None:

        print(f"repositories/project_repository.py Fetching project with ID {project_id} from the database")

        return db.scalar(select(Project).options(selectinload(Project.creator), selectinload(Project.issues)).where(Project.id == project_id, Project.is_active == True))



    def create(self, db: Session, project: Project) -> Project:

        print(f"repositories/project_repository.py Creating a new project with name '{project.name}' in the database")

        db.add(project); db.commit(); db.refresh(project)

        return self.get(db, project.id)  # type: ignore[return-value]



    def delete(self, db: Session, project: Project) -> None:

        print(f"repositories/project_repository.py Soft-deleting project with ID {project.id} from the database")

        project.is_active = False

        db.commit()



    def create(self, db: Session, project: Project) -> Project:

        print(f"repositories/project_repository.py Creating a new project with name '{project.name}' in the database")

        db.add(project); db.commit(); db.refresh(project)

        return self.get(db, project.id)  # type: ignore[return-value]



    def delete(self, db: Session, project: Project) -> None:

        print(f"repositories/project_repository.py Soft-deleting project with ID {project.id} from the database")

        project.is_active = False

        db.commit()


"""Database schema initialization and seed data script.
Used to create all tables and initial seed data directly via SQLAlchemy metadata.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal
# Import all models to ensure they are registered on Base.metadata
import app.models  # noqa: F401
from app.models.issue import (
    IssueStatus,
    IssuePriority,
    IssueSeverity,
    IssueCategory,
    IssueModule,
)
from app.models.sprint import SprintStatus
from app.models.role import Role, Permission, role_permissions
from app.models.team import Team


def init_db() -> None:
    print("Creating all database tables via SQLAlchemy metadata...")
    Base.metadata.create_all(bind=engine)

    # Enable HNSW vector index on issues.embedding_vector if vector extension is present
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_issues_embedding_vector_hnsw
                ON issues
                USING hnsw (embedding_vector vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: Vector index creation skipped/failed: {e}")

    # Seed initial lookup tables, roles, and permissions
    db: Session = SessionLocal()
    try:
        # 1. Issue Statuses
        statuses = ["Open", "In Progress", "Resolved", "Closed"]
        for name in statuses:
            if not db.query(IssueStatus).filter(IssueStatus.name == name).first():
                db.add(IssueStatus(name=name, is_active=True))

        # 2. Issue Priorities
        priorities = ["Low", "Medium", "High", "Critical"]
        for name in priorities:
            if not db.query(IssuePriority).filter(IssuePriority.name == name).first():
                db.add(IssuePriority(name=name, is_active=True))

        # 3. Issue Severities
        severities = ["Low", "Medium", "High", "Critical"]
        for name in severities:
            if not db.query(IssueSeverity).filter(IssueSeverity.name == name).first():
                db.add(IssueSeverity(name=name, is_active=True))

        # 4. Issue Categories
        categories = ["UI", "Backend", "Database", "API"]
        for name in categories:
            if not db.query(IssueCategory).filter(IssueCategory.name == name).first():
                db.add(IssueCategory(name=name, is_active=True))

        # 5. Issue Modules
        modules = ["Authentication", "User Management", "Reporting", "Notifications"]
        for name in modules:
            if not db.query(IssueModule).filter(IssueModule.name == name).first():
                db.add(IssueModule(name=name, is_active=True))

        # 6. Sprint Statuses
        sprint_statuses = ["Planned", "Active", "Completed"]
        for name in sprint_statuses:
            if not db.query(SprintStatus).filter(SprintStatus.name == name).first():
                db.add(SprintStatus(name=name, is_active=True))

        # 7. Roles
        roles_data = [
            ("Admin", "Administrator with full access"),
            ("Developer", "Developer role"),
            ("QA", "Quality Assurance role"),
            ("Reporter", "Reporter role"),
            ("Project Manager", "Manages projects and sprints"),
            ("Team Leader", "Leads development team"),
        ]
        for name, desc in roles_data:
            if not db.query(Role).filter(Role.name == name).first():
                db.add(Role(name=name, description=desc))

        # 8. Permissions
        permissions_data = [
            ("view_issues", "Can view issues"),
            ("create_issues", "Can create issues"),
            ("edit_issues", "Can edit issues"),
            ("delete_issues", "Can delete issues"),
            ("manage_projects", "Can manage projects"),
            ("manage_sprints", "Can manage sprints"),
            ("manage_teams", "Can manage teams"),
            ("manage_users", "Can manage users"),
            ("manage_roles", "Can manage roles and permissions"),
            ("view_reports", "Can view reports"),
        ]
        for name, desc in permissions_data:
            if not db.query(Permission).filter(Permission.name == name).first():
                db.add(Permission(name=name, description=desc))

        db.commit()

        # 9. Role-Permission mappings
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        all_perms = db.query(Permission).all()
        if admin_role:
            for p in all_perms:
                exists = db.execute(
                    text("SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
                    {"r": admin_role.id, "p": p.id}
                ).first()
                if not exists:
                    db.execute(
                        text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                        {"r": admin_role.id, "p": p.id}
                    )

        # Basic perms for Developer, QA, Reporter
        basic_perm_names = ["view_issues", "create_issues", "edit_issues"]
        basic_perms = db.query(Permission).filter(Permission.name.in_(basic_perm_names)).all()
        for role_name in ["Developer", "QA", "Reporter"]:
            r = db.query(Role).filter(Role.name == role_name).first()
            if r:
                for p in basic_perms:
                    exists = db.execute(
                        text("SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
                        {"r": r.id, "p": p.id}
                    ).first()
                    if not exists:
                        db.execute(
                            text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                            {"r": r.id, "p": p.id}
                        )

        # PM perms
        pm_perm_names = ["view_issues", "edit_issues", "manage_projects", "manage_sprints"]
        pm_perms = db.query(Permission).filter(Permission.name.in_(pm_perm_names)).all()
        pm_role = db.query(Role).filter(Role.name == "Project Manager").first()
        if pm_role:
            for p in pm_perms:
                exists = db.execute(
                    text("SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
                    {"r": pm_role.id, "p": p.id}
                ).first()
                if not exists:
                    db.execute(
                        text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                        {"r": pm_role.id, "p": p.id}
                    )

        # TL perms
        tl_perm_names = ["view_issues", "edit_issues", "manage_teams", "manage_users"]
        tl_perms = db.query(Permission).filter(Permission.name.in_(tl_perm_names)).all()
        tl_role = db.query(Role).filter(Role.name == "Team Leader").first()
        if tl_role:
            for p in tl_perms:
                exists = db.execute(
                    text("SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
                    {"r": tl_role.id, "p": p.id}
                ).first()
                if not exists:
                    db.execute(
                        text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                        {"r": tl_role.id, "p": p.id}
                    )

        # 10. Default Core Team
        core_team = db.query(Team).filter(Team.name == "BugForge Core Team").first()
        if not core_team:
            db.add(Team(
                name="BugForge Core Team",
                description="Primary engineering and cross-functional defect resolution team",
                is_active=True
            ))

        db.commit()
        print("Database schema and seed data initialized successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error during database initialization: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

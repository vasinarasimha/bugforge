"""Database schema initialization and seed data script.
Used to create all tables and initial seed data directly via SQLAlchemy metadata.
"""
import os
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
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
from app.models.company import Company, CompanySettings
from app.models.user import User
from app.models.project_history import ProjectHistory  # noqa: F401


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
        # 0. Default Company
        default_company = db.query(Company).filter(Company.name == "BugForge").first()
        if not default_company:
            default_company = Company(
                name="BugForge",
                legal_name="BugForge Inc.",
                timezone="UTC",
                is_active=True
            )
            db.add(default_company)
            db.flush()  # Get the ID
            # Create default settings
            db.add(CompanySettings(company_id=default_company.id, settings={}))
        company_id = default_company.id

        # 1. Issue Statuses (company default & global fallback)
        default_statuses = [
            {"name": "Open", "category": "open", "color": "#3b82f6", "order_index": 1, "is_initial": True, "is_final": False},
            {"name": "In Progress", "category": "in_progress", "color": "#8b5cf6", "order_index": 2, "is_initial": False, "is_final": False},
            {"name": "Resolved", "category": "resolved", "color": "#10b981", "order_index": 3, "is_initial": False, "is_final": False},
            {"name": "Verified", "category": "resolved", "color": "#06b6d4", "order_index": 4, "is_initial": False, "is_final": False},
            {"name": "Closed", "category": "closed", "color": "#64748b", "order_index": 5, "is_initial": False, "is_final": True},
        ]
        # A. Seed for BugForge company
        for s_def in default_statuses:
            existing = db.query(IssueStatus).filter(
                IssueStatus.name == s_def["name"],
                IssueStatus.company_id == company_id,
            ).first()
            if not existing:
                db.add(IssueStatus(
                    name=s_def["name"],
                    category=s_def["category"],
                    color=s_def["color"],
                    order_index=s_def["order_index"],
                    is_initial=s_def["is_initial"],
                    is_final=s_def["is_final"],
                    is_active=True,
                    company_id=company_id,
                ))
            elif existing.category != s_def["category"]:
                existing.category = s_def["category"]

        # B. Seed global fallbacks (company_id is None)
        for s_def in default_statuses:
            existing_global = db.query(IssueStatus).filter(
                IssueStatus.name == s_def["name"],
                IssueStatus.company_id.is_(None),
            ).first()
            if not existing_global:
                db.add(IssueStatus(
                    name=s_def["name"],
                    category=s_def["category"],
                    color=s_def["color"],
                    order_index=s_def["order_index"],
                    is_initial=s_def["is_initial"],
                    is_final=s_def["is_final"],
                    is_active=True,
                    company_id=None,
                ))
            elif existing_global.category != s_def["category"]:
                existing_global.category = s_def["category"]

        # 2. Issue Priorities (global)
        priorities = ["Low", "Medium", "High", "Critical"]
        for name in priorities:
            if not db.query(IssuePriority).filter(IssuePriority.name == name).first():
                db.add(IssuePriority(name=name, is_active=True))

        # 3. Issue Severities (global)
        severities = ["Low", "Medium", "High", "Critical"]
        for name in severities:
            if not db.query(IssueSeverity).filter(IssueSeverity.name == name).first():
                db.add(IssueSeverity(name=name, is_active=True))

        # 4. Issue Categories (company-scoped)
        categories = ["UI", "Backend", "Database", "API"]
        for name in categories:
            if not db.query(IssueCategory).filter(
                IssueCategory.name == name, IssueCategory.company_id == company_id
            ).first():
                db.add(IssueCategory(name=name, is_active=True, company_id=company_id))

        # 5. Issue Modules (company-scoped)
        modules = ["Authentication", "User Management", "Reporting", "Notifications"]
        for name in modules:
            if not db.query(IssueModule).filter(
                IssueModule.name == name, IssueModule.company_id == company_id
            ).first():
                db.add(IssueModule(name=name, is_active=True, company_id=company_id))

        # 6. Sprint Statuses
        sprint_statuses = ["Planned", "Active", "Completed"]
        for name in sprint_statuses:
            if not db.query(SprintStatus).filter(SprintStatus.name == name).first():
                db.add(SprintStatus(name=name, is_active=True))

        # 7. Roles
        roles_data = [
            ("Super Admin", "Platform-level administrator with access to all companies"),
            ("Admin", "Company administrator with full access within their company"),
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

        # 10. Default Core Team (with company_id)
        core_team = db.query(Team).filter(Team.name == "BugForge Core Team").first()
        if not core_team:
            db.add(Team(
                name="BugForge Core Team",
                description="Primary engineering and cross-functional defect resolution team",
                company_id=company_id,
                is_active=True
            ))

        # 11. Super Admin user (from environment variables or defaults)
        super_admin_email = os.environ.get("SUPER_ADMIN_EMAIL", "vln@superadmin.in")
        super_admin_password = os.environ.get("SUPER_ADMIN_PASSWORD", "admin@123")
        existing_super = db.query(User).filter(User.email == super_admin_email.lower()).first()
        if not existing_super:
            super_role = db.query(Role).filter(Role.name == "Super Admin").first()
            if super_role:
                super_user = User(
                    full_name="Super Admin",
                    email=super_admin_email.lower().strip(),
                    password_hash=hash_password(super_admin_password),
                    is_active=True,
                    is_system_user=False,
                    company_id=None,  # Super Admin has no company
                )
                db.add(super_user)
                db.flush()
                super_user.roles = [super_role]
                print(f"Created Super Admin user: {super_admin_email}")

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

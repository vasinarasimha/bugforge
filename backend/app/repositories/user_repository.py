from __future__ import annotations
from typing import Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.role import Role


class UserRepository:
    def get_by_email(self, db: Session, email: str, include_inactive: bool = False) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.lower().strip())
        if not include_inactive:
            stmt = stmt.where(User.is_active == True)
        return db.scalar(stmt)

    def get_by_id(self, db: Session, user_id: int, include_inactive: bool = False, company_id: Optional[int] = None) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if not include_inactive:
            stmt = stmt.where(User.is_active == True)
        if company_id is not None:
            stmt = stmt.where(User.company_id == company_id)
        return db.scalar(stmt)

    def get_role_by_name(self, db: Session, name: str) -> Role | None:
        return db.scalar(select(Role).where(Role.name == name))

    def get_or_create_role(self, db: Session, name: str) -> Role:
        role = self.get_role_by_name(db, name)
        if not role:
            role = Role(name=name, description=f"{name} role")
            db.add(role)
            db.commit()
            db.refresh(role)
        return role

    def get_all_roles(self, db: Session) -> list[Role]:
        # Ensure all UserRole enums exist in DB
        for enum_role in UserRole:
            role_obj = db.scalar(select(Role).where(Role.name == enum_role.value))
            if not role_obj:
                db.add(Role(name=enum_role.value, description=f"{enum_role.value} role"))
        db.commit()
        return list(db.scalars(select(Role).order_by(Role.id)).all())

    def assign_role(self, db: Session, user: User, role_name: str) -> None:
        role = self.get_or_create_role(db, role_name)
        user.roles = [role]
        db.commit()
        db.refresh(user)

    def assign_roles(self, db: Session, user: User, role_names: list[str]) -> None:
        roles = [self.get_or_create_role(db, rname) for rname in role_names if rname]
        if roles:
            user.roles = roles
            db.commit()
            db.refresh(user)

    def create(self, db: Session, user: User, role_name: Optional[str] = None) -> User:
        user.email = user.email.lower().strip()
        db.add(user)
        db.flush()  # Flush to get user.id before relationship mapping
        if role_name:
            role = self.get_or_create_role(db, role_name)
            user.roles = [role]
        db.commit()
        db.refresh(user)
        return user

    def update(self, db: Session, user: User, update_data: dict) -> User:
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user

    def list(self, db: Session, include_system: bool = False, company_id: Optional[int] = None) -> list[User]:
        stmt = select(User).where(User.is_active == True)
        if not include_system:
            stmt = stmt.where(User.is_system_user == False)
        if company_id is not None:
            stmt = stmt.where(User.company_id == company_id)
        return list(db.scalars(stmt))

    def list_employees(
        self,
        db: Session,
        search: Optional[str] = None,
        role_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        include_system: bool = False,
        limit: int = 50,
        offset: int = 0,
        company_id: Optional[int] = None,
    ) -> Tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count(User.id))

        if not include_system:
            stmt = stmt.where(User.is_system_user == False)
            count_stmt = count_stmt.where(User.is_system_user == False)

        if company_id is not None:
            stmt = stmt.where(User.company_id == company_id)
            count_stmt = count_stmt.where(User.company_id == company_id)

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
            count_stmt = count_stmt.where(User.is_active == is_active)

        if search and search.strip():
            term = f"%{search.strip()}%"
            filter_condition = or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
                User.job_title.ilike(term),
                User.department.ilike(term),
                User.city.ilike(term),
                User.country.ilike(term)
            )
            stmt = stmt.where(filter_condition)
            count_stmt = count_stmt.where(filter_condition)

        if role_name and role_name.strip():
            stmt = stmt.join(User.roles).where(Role.name == role_name.strip())
            count_stmt = count_stmt.join(User.roles).where(Role.name == role_name.strip())

        total = db.scalar(count_stmt) or 0
        users = list(db.scalars(stmt.order_by(User.id.desc()).limit(limit).offset(offset)).unique().all())
        return users, total

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AdminUserCreate, AdminUserUpdate, SelfProfileUpdate


class AuthService:
    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def authenticate_user(self, db: Session, email: str, password: str) -> User | None:
        # Check by email including inactive to give clear error if deactivated
        user = self.user_repository.get_by_email(db, email, include_inactive=True)
        if not user or not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact your administrator.",
            )
        return user

    def create_employee(self, db: Session, employee_data: AdminUserCreate) -> User:
        # Check duplicate email
        existing = self.user_repository.get_by_email(db, str(employee_data.email), include_inactive=True)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists.",
            )

        user = User(
            full_name=employee_data.full_name.strip(),
            email=str(employee_data.email).lower().strip(),
            password_hash=hash_password(employee_data.password),
            job_title=employee_data.job_title.strip() if employee_data.job_title else None,
            department=employee_data.department.strip() if employee_data.department else None,
            mobile_country_code=employee_data.mobile_country_code.strip() if employee_data.mobile_country_code else None,
            mobile_number=employee_data.mobile_number.strip() if employee_data.mobile_number else None,
            address_line_1=employee_data.address_line_1.strip() if employee_data.address_line_1 else None,
            address_line_2=employee_data.address_line_2.strip() if employee_data.address_line_2 else None,
            city=employee_data.city.strip() if employee_data.city else None,
            state=employee_data.state.strip() if employee_data.state else None,
            state_code=employee_data.state_code.strip() if employee_data.state_code else None,
            country=employee_data.country.strip() if employee_data.country else None,
            country_code=employee_data.country_code.strip() if employee_data.country_code else None,
            is_active=True,
        )

        role_name = employee_data.role or (employee_data.roles[0] if employee_data.roles else "Developer")
        user = self.user_repository.create(db, user, role_name=role_name)
        if employee_data.roles and len(employee_data.roles) > 1:
            self.user_repository.assign_roles(db, user, employee_data.roles)
        return user

    def update_user_admin(
        self, db: Session, user_id: int, update_data: AdminUserUpdate, current_admin: User
    ) -> User:
        user = self.user_repository.get_by_id(db, user_id, include_inactive=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {user_id} not found.",
            )

        # Prevent admin from deactivating their own account
        if update_data.is_active is False and user.id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate their own account.",
            )

        update_dict = {}
        data = update_data.model_dump(exclude_unset=True)

        if "email" in data and data["email"]:
            new_email = str(data["email"]).lower().strip()
            if new_email != user.email:
                existing = self.user_repository.get_by_email(db, new_email, include_inactive=True)
                if existing and existing.id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Another account with this email address already exists.",
                    )
                update_dict["email"] = new_email

        if "password" in data and data["password"]:
            update_dict["password_hash"] = hash_password(data["password"])

        for field in [
            "full_name", "job_title", "department", "mobile_country_code", "mobile_number",
            "address_line_1", "address_line_2", "city", "state", "state_code", "country", "country_code",
            "is_active"
        ]:
            if field in data:
                val = data[field]
                update_dict[field] = val.strip() if isinstance(val, str) else val

        if update_dict:
            user = self.user_repository.update(db, user, update_dict)

        # Role updates
        if "role" in data and data["role"]:
            self.user_repository.assign_role(db, user, data["role"])
        elif "roles" in data and data["roles"]:
            self.user_repository.assign_roles(db, user, data["roles"])

        return user

    def update_self_profile(self, db: Session, user_id: int, profile_data: SelfProfileUpdate) -> User:
        user = self.user_repository.get_by_id(db, user_id, include_inactive=False)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive.",
            )

        data = profile_data.model_dump(exclude_unset=True)
        update_dict = {}
        for field in [
            "full_name", "job_title", "department", "mobile_country_code", "mobile_number",
            "address_line_1", "address_line_2", "city", "state", "state_code", "country", "country_code"
        ]:
            if field in data:
                val = data[field]
                update_dict[field] = val.strip() if isinstance(val, str) else val

        if update_dict:
            user = self.user_repository.update(db, user, update_dict)
        return user

    def deactivate_user(self, db: Session, user_id: int, current_admin: User) -> User:
        user = self.user_repository.get_by_id(db, user_id, include_inactive=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {user_id} not found.",
            )
        if user.id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate their own account.",
            )
        return self.user_repository.update(db, user, {"is_active": False})

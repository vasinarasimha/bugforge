from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate


class AuthService:
    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def register_user(self, db: Session, user_data: UserCreate) -> User | None:
        print(f"services/auth_service.py Registering new user with email: {user_data.email}")
        if self.user_repository.get_by_email(db, str(user_data.email)):
            print("services/auth_service.py User with this email already exists")
            return None

        user = User(
            full_name=user_data.full_name.strip(),
            email=str(user_data.email).lower(),
            password_hash=hash_password(user_data.password),
            # role handling will be done via roles mapping if needed
        )
        print(f"services/auth_service.py User registered successfully: {user.full_name}")
        return self.user_repository.create(db, user)

    def authenticate_user(self, db: Session, email: str, password: str) -> User | None:
        print(f"services/auth_service.py Authenticating user with email: {email}")
        user = self.user_repository.get_by_email(db, email)
        if not user or not verify_password(password, user.password_hash):
            print("services/auth_service.py Authentication failed: Invalid email or password")
            return None
        print(f"services/auth_service.py User authenticated successfully: {user.full_name}")
        return user

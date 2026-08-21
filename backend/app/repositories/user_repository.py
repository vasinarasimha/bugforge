from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User

class UserRepository:
    def get_by_email(self, db: Session, email: str) -> User | None:
        print(f"repositories/user_repository.py Fetching user with email {email} from the database")
        return db.scalar(select(User).where(User.email == email.lower(), User.is_active == True))

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        print(f"repositories/user_repository.py Fetching user with ID {user_id} from the database")
        return db.scalar(select(User).where(User.id == user_id, User.is_active == True))

    def create(self, db: Session, user: User) -> User:
        print(f"repositories/user_repository.py Creating a new user with email '{user.email}' in the database")
        user.email = user.email.lower()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def list(self, db: Session) -> list[User]:
        print("repositories/user_repository.py Fetching all users from the database")
        return list(db.scalars(select(User).where(User.is_active == True)))

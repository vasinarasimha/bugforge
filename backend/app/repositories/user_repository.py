from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def get_by_email(self, db: Session, email: str) -> User | None:
        # print(f"repositories/user_repository.py Fetching user with email {email} from the database")
        return db.scalar(select(User).where(User.email == email.lower()))

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        # print(f"repositories/user_repository.py Fetching user with ID {user_id} from the database")
        return db.get(User, user_id)

    def create(self, db: Session, user: User) -> User:
        # print(f"repositories/user_repository.py Creating a new user with email '{user.email}' in the database")
        user.email = user.email.lower()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

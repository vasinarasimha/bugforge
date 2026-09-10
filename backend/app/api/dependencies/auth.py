from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(credentials.credentials)
    if user_id is None or not str(user_id).isdigit():
        raise unauthorized

    user = UserRepository().get_by_id(db, int(user_id), include_inactive=True)
    if user is None:
        raise unauthorized
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated. Please contact an administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(allowed_roles: list[Any]):
    # Normalize allowed roles to string names
    normalized_allowed = [
        r.value if hasattr(r, "value") else str(r) for r in allowed_roles
    ]

    def role_checker(current_user: User = Depends(get_current_user)):
        user_roles = [r.name for r in getattr(current_user, "roles", [])]
        if "Super Admin" in user_roles:
            return current_user
        if not any(role in normalized_allowed for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    user = auth_service.register_user(db, user_data)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Annotated[Session, Depends(get_db)]) -> Token:
    user = auth_service.authenticate_user(db, str(credentials.email), credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)), user=user)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user

@router.get("/users")
def get_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    search: str = "",
    limit: int = 100,
    offset: int = 0
):
    from sqlalchemy import select
    stmt = select(User).where(User.is_active == True)
    if search:
        stmt = stmt.where(User.full_name.ilike(f"%{search}%"))
    stmt = stmt.limit(limit).offset(offset)
    users = db.scalars(stmt).all()
    
    return {
        "data": [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "roles": [{"name": r.name} for r in getattr(u, 'roles', [])]
            } for u in users
        ]
    }

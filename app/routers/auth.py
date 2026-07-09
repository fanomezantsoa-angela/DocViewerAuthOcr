# app/routers/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import login_user, register_user
from app.db.base import get_db
from app.schemas.auth import Token, UserCreate, UserLogin


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> Token:
    return Token(access_token=register_user(db, user_in))


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    return Token(access_token=login_user(db, credentials))

# app/modules/auth/routes.py
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi import Body

from app.db.deps import get_db
from app.modules.auth.service import AuthService
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserCreate = Body(...),
    db: Session = Depends(get_db),
):
    """Register a new user."""
    auth_service = AuthService(db)
    user = auth_service.register_user(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        db=db,
    )
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login user and return JWT token."""
    auth_service = AuthService(db)
    access_token = auth_service.login(
        email=form_data.username,
        password=form_data.password,
    )
    return Token(access_token=access_token)


@router.post("/verify", response_model=Token)
def verify_user(
    token: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    tokens = auth_service.verify_user(token=token, db=db)
    return Token(**tokens)

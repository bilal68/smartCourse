from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.modules.registration.service import RegistrationService
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import Token

router = APIRouter(prefix="/registration", tags=["registration"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate = Body(...), db: Session = Depends(get_db)):
    reg_service = RegistrationService(db)
    user = reg_service.register_user(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password
    )
    return user

@router.post("/verify", response_model=Token)
def verify_user(token: str = Body(..., embed=True), db: Session = Depends(get_db)):
    reg_service = RegistrationService(db)
    tokens = reg_service.verify_user(token=token)
    return Token(**tokens)

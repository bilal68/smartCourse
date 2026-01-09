from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password, create_access_token
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository, RoleRepository
from app.core.logging import get_logger
from datetime import timedelta
from app.core.config import settings

logger = get_logger(__name__)


class AuthService:
    """Service layer for authentication operations."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    def register_user(self, email: str, full_name: str, password: str) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = self.user_repo.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password and create user
        password_hash = get_password_hash(password)
        user = self.user_repo.create(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
        )
        
        self.db.commit()
        self.db.refresh(user)
        
        logger.info("registered user", user_id=str(user.id), email=user.email)
        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user

    def login(self, email: str, password: str) -> str:
        """Login user and return access token."""
        user = self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect email or password",
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
        )

        logger.info("user logged in", user_id=str(user.id), email=user.email)
        return access_token

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return self.user_repo.get_by_id(user_id)

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.modules.auth.models import UserStatus
from app.modules.auth.models import VerificationToken
from app.modules.auth.models import Role
from app.modules.auth.repository import UserRoleRepository
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from datetime import datetime, timedelta
import secrets

from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository, RoleRepository
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class AuthService:
    """Service layer for authentication operations."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    def register_user(self, email: str, full_name: str, password: str, db: Session) -> User:
        # Validate input
        if not email or not password or not full_name:
            raise HTTPException(status_code=400, detail="Missing required fields")
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        password_hash = get_password_hash(password)
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)
        try:
            # Start transaction
            user = User(email=email, full_name=full_name, password_hash=password_hash, status=UserStatus.pending)
            db.add(user)
            db.flush()
            # Assign default role
            student_role = db.query(Role).filter(Role.name == "student").first()
            if not student_role:
                student_role = Role(name="student")
                db.add(student_role)
                db.flush()
            user_role = UserRoleRepository(db).assign_role(user.id, student_role.id)
            # Verification token
            vtoken = VerificationToken(user_id=user.id, token=token, expires_at=expiry)
            db.add(vtoken)
            # Outbox event
            outbox = OutboxEvent(
                event_type="user.registered",
                aggregate_type="user",
                aggregate_id=user.id,
                payload={"user_id": str(user.id), "email": email},
                status=OutboxStatus.pending,
                attempts=0,
            )
            db.add(outbox)
            db.commit()
            db.refresh(user)
            return user
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    def verify_user(self, token: str, db: Session):
        vtoken = db.query(VerificationToken).filter(VerificationToken.token == token).first()
        if not vtoken or vtoken.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        try:
            user = db.query(User).filter(User.id == vtoken.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.status = UserStatus.active
            db.delete(vtoken)
            outbox = OutboxEvent(
                event_type="user.verified",
                aggregate_type="user",
                aggregate_id=user.id,
                payload={"user_id": str(user.id), "email": user.email},
                status=OutboxStatus.pending,
                attempts=0,
            )
            db.add(outbox)
            db.commit()
            access_token = create_access_token(subject=str(user.id))
            refresh_token = create_refresh_token(subject=str(user.id))
            return {"access_token": access_token, "refresh_token": refresh_token}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

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

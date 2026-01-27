from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.modules.auth.models import UserStatus, VerificationToken, Role
from app.modules.auth.repository import UserRoleRepository
from app.core.security import get_password_hash, create_access_token, create_refresh_token
from datetime import datetime, timedelta
import secrets

class RegistrationService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, email: str, full_name: str, password: str):
        if not email or not password or not full_name:
            raise HTTPException(status_code=400, detail="Missing required fields")
        if self.db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        password_hash = get_password_hash(password)
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)
        try:
            user = User(email=email, full_name=full_name, password_hash=password_hash, status=UserStatus.pending)
            self.db.add(user)
            self.db.flush()
            student_role = self.db.query(Role).filter(Role.name == "student").first()
            if not student_role:
                student_role = Role(name="student")
                self.db.add(student_role)
                self.db.flush()
            UserRoleRepository(self.db).assign_role(user.id, student_role.id)
            vtoken = VerificationToken(user_id=user.id, token=token, expires_at=expiry)
            self.db.add(vtoken)
            outbox = OutboxEvent(
                event_type="user.registered",
                aggregate_type="user",
                aggregate_id=user.id,
                payload={"user_id": str(user.id), "email": email},
                status=OutboxStatus.pending,
                attempts=0,
            )
            self.db.add(outbox)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    def verify_user(self, token: str):
        vtoken = self.db.query(VerificationToken).filter(VerificationToken.token == token).first()
        if not vtoken or vtoken.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        try:
            user = self.db.query(User).filter(User.id == vtoken.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.status = UserStatus.active
            self.db.delete(vtoken)
            outbox = OutboxEvent(
                event_type="user.verified",
                aggregate_type="user",
                aggregate_id=user.id,
                payload={"user_id": str(user.id), "email": user.email},
                status=OutboxStatus.pending,
                attempts=0,
            )
            self.db.add(outbox)
            self.db.commit()
            access_token = create_access_token(subject=str(user.id))
            refresh_token = create_refresh_token(subject=str(user.id))
            return {"access_token": access_token, "refresh_token": refresh_token}
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

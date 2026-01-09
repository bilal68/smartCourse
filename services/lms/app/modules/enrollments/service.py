from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from app.modules.enrollments.repository import EnrollmentRepository
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.courses.repository import CourseRepository
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class EnrollmentService:
    """Service layer for enrollment operations."""

    def __init__(self, db: Session):
        self.db = db
        self.enrollment_repo = EnrollmentRepository(db)
        self.user_repo = UserRepository(db)
        self.course_repo = CourseRepository(db)

    def create_enrollment(
        self,
        user_id: uuid.UUID,
        course_id: uuid.UUID,
        status: EnrollmentStatus,
        source: Optional[str],
        current_user: User,
    ) -> Enrollment:
        """Create a new enrollment with authorization checks."""
        # Permission check: students can only enroll themselves; instructors/admins can enroll others
        role_names = [r.name for r in (current_user.roles or [])]
        if (
            current_user.id != user_id
            and "instructor" not in role_names
            and "admin" not in role_names
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only enroll yourself; instructors/admins can enroll others",
            )

        # Ensure user exists
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Ensure course exists
        course = self.course_repo.get_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Idempotency: check if already enrolled
        existing = self.enrollment_repo.get_by_user_and_course(user_id, course_id)
        if existing:
            return existing

        # Create enrollment
        enrollment = self.enrollment_repo.create(
            user_id=user_id,
            course_id=course_id,
            status=status,
            source=source,
        )

        # Create outbox event for enrollment.created
        outbox = OutboxEvent(
            event_type="enrollment.created",
            aggregate_type="enrollment",
            aggregate_id=enrollment.id,
            payload={
                "enrollment_id": str(enrollment.id),
                "user_id": str(enrollment.user_id),
                "course_id": str(enrollment.course_id),
                "status": (
                    enrollment.status.value
                    if hasattr(enrollment.status, "value")
                    else str(enrollment.status)
                ),
                "source": enrollment.source,
                "enrolled_at": datetime.utcnow().isoformat(),
            },
            status=OutboxStatus.pending,
            attempts=0,
        )

        self.db.add(outbox)
        self.db.commit()
        self.db.refresh(enrollment)

        logger.info(
            "created enrollment",
            enrollment_id=str(enrollment.id),
            user_id=str(enrollment.user_id),
            course_id=str(enrollment.course_id),
        )
        return enrollment

    def get_enrollment(self, enrollment_id: uuid.UUID) -> Enrollment:
        """Get enrollment by ID."""
        enrollment = self.enrollment_repo.get_by_id(enrollment_id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )
        return enrollment

    def list_enrollments_by_user(self, user_id: uuid.UUID) -> list[Enrollment]:
        """List all enrollments for a user."""
        return self.enrollment_repo.list_by_user(user_id)

    def list_enrollments_by_course(self, course_id: uuid.UUID) -> list[Enrollment]:
        """List all enrollments for a course."""
        return self.enrollment_repo.list_by_course(course_id)

    def update_enrollment(
        self,
        enrollment_id: uuid.UUID,
        current_user: User,
        **update_data,
    ) -> Enrollment:
        """Update enrollment with authorization checks."""
        enrollment = self.get_enrollment(enrollment_id)

        # Permission check: user can only update their own enrollment; admins can update any
        role_names = [r.name for r in (current_user.roles or [])]
        if enrollment.user_id != current_user.id and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own enrollment",
            )

        enrollment = self.enrollment_repo.update(enrollment, **update_data)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def delete_enrollment(self, enrollment_id: uuid.UUID, current_user: User) -> None:
        """Delete enrollment with authorization checks."""
        enrollment = self.get_enrollment(enrollment_id)

        # Permission check: user can only delete their own enrollment; admins can delete any
        role_names = [r.name for r in (current_user.roles or [])]
        if enrollment.user_id != current_user.id and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own enrollment",
            )

        self.enrollment_repo.delete(enrollment)
        self.db.commit()

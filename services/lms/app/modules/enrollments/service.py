from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from app.modules.enrollments.repository import EnrollmentRepository
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.courses.models import CourseStatus
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
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You can only enroll yourself; instructors/admins can enroll others",
            )

        # Ensure user exists
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Ensure course exists
        course = self.course_repo.get_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # NEW: Check course status - cannot enroll in archived courses
        if course.status == CourseStatus.archived:
            logger.warning(f"Attempt to enroll in archived course: {course_id}")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cannot enroll in archived course",
            )

        # NEW: Check prerequisites
        incomplete_prereqs = self.enrollment_repo.get_incomplete_prerequisites(user_id, course)
        if incomplete_prereqs:
            prereq_titles = ", ".join([c.title for c in incomplete_prereqs])
            logger.warning(
                f"User {user_id} missing prerequisites for course {course_id}: {prereq_titles}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Prerequisites not met",
                    "missing_prerequisites": [
                        {
                            "id": str(c.id),
                            "title": c.title,
                            "description": c.description
                        }
                        for c in incomplete_prereqs
                    ],
                    "message": f"You must complete the following courses first: {prereq_titles}"
                }
            )

        # NEW: Check enrollment limit
        if course.max_students is not None:
            active_count = self.enrollment_repo.count_active_enrollments(course_id)
            if active_count >= course.max_students:
                logger.warning(
                    f"Course {course_id} is full: {active_count}/{course.max_students}"
                )
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Course is full. Maximum capacity: {course.max_students}",
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

        # Trigger post-enrollment orchestration (async)
        from app.tasks.enrollment_tasks import handle_enrollment_post_actions
        handle_enrollment_post_actions.delay(str(enrollment.id))

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
                status_code=http_status.HTTP_404_NOT_FOUND,
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
                status_code=http_status.HTTP_403_FORBIDDEN,
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
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own enrollment",
            )

        self.enrollment_repo.delete(enrollment)
        self.db.commit()

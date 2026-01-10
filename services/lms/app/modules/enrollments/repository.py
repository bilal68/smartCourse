from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from app.modules.courses.models import Course


class EnrollmentRepository:
    """Repository for Enrollment entity with CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, enrollment_id: uuid.UUID) -> Optional[Enrollment]:
        """Get enrollment by ID."""
        return self.db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()

    def get_by_user_and_course(
        self, user_id: uuid.UUID, course_id: uuid.UUID
    ) -> Optional[Enrollment]:
        """Get enrollment by user and course."""
        return (
            self.db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
            )
            .first()
        )

    def list_by_user(self, user_id: uuid.UUID) -> list[Enrollment]:
        """List all enrollments for a user."""
        return self.db.query(Enrollment).filter(Enrollment.user_id == user_id).all()

    def list_by_course(self, course_id: uuid.UUID) -> list[Enrollment]:
        """List all enrollments for a course."""
        return self.db.query(Enrollment).filter(Enrollment.course_id == course_id).all()

    def create(
        self,
        user_id: uuid.UUID,
        course_id: uuid.UUID,
        status: EnrollmentStatus = EnrollmentStatus.active,
        source: Optional[str] = None,
    ) -> Enrollment:
        """Create a new enrollment."""
        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            status=status,
            source=source,
        )
        self.db.add(enrollment)
        self.db.flush()
        return enrollment

    def update(self, enrollment: Enrollment, **kwargs) -> Enrollment:
        """Update enrollment fields."""
        for key, value in kwargs.items():
            if hasattr(enrollment, key):
                setattr(enrollment, key, value)
        self.db.flush()
        return enrollment

    def delete(self, enrollment: Enrollment) -> None:
        """Delete enrollment."""
        self.db.delete(enrollment)
        self.db.flush()

    def has_completed_course(self, user_id: uuid.UUID, course_id: uuid.UUID) -> bool:
        """Check if user has completed a specific course."""
        enrollment = (
            self.db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.completed
            )
            .first()
        )
        return enrollment is not None

    def get_incomplete_prerequisites(
        self, 
        user_id: uuid.UUID, 
        course: Course
    ) -> list[Course]:
        """Get list of prerequisite courses user hasn't completed."""
        incomplete = []
        
        for prereq_course in course.prerequisites:
            if not self.has_completed_course(user_id, prereq_course.id):
                incomplete.append(prereq_course)
        
        return incomplete

    def count_active_enrollments(self, course_id: uuid.UUID) -> int:
        """Count active enrollments in a course."""
        count = (
            self.db.query(func.count(Enrollment.id))
            .filter(
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.active
            )
            .scalar()
        )
        return count or 0

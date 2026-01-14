from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.courses.models import Course, Module, LearningAsset, CourseStatus, CourseProcessingStatus
from app.modules.courses.repository import CourseRepository, ModuleRepository, LearningAssetRepository
from app.modules.auth.models import User
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class CourseService:
    """Service layer for course operations."""

    def __init__(self, db: Session):
        self.db = db
        self.course_repo = CourseRepository(db)
        self.module_repo = ModuleRepository(db)

    def create_course(
        self,
        title: str,
        description: Optional[str],
        course_status: CourseStatus,
        instructor_id: Optional[uuid.UUID],
        user: User,
    ) -> Course:
        """Create a new course with authorization checks."""
        # Check authorization
        role_names = [r.name for r in (user.roles or [])]
        if "instructor" not in role_names and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only instructors or admins can create courses",
            )

        # Handle instructor_id assignment
        if instructor_id:
            if "admin" not in role_names and instructor_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You may not set instructor_id for other users",
                )
        else:
            instructor_id = user.id if "instructor" in role_names else None

        course = self.course_repo.create(
            title=title,
            description=description,
            status=course_status,
            instructor_id=instructor_id,
        )
        
        self.db.commit()
        self.db.refresh(course)
        
        logger.info("created course", course_id=str(course.id), title=course.title)
        return course

    def get_course(self, course_id: uuid.UUID, public: bool = True) -> Course:
        """Get course by ID with visibility checks."""
        course = self.course_repo.get_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # If public access, only show published courses
        if public and course.status != CourseStatus.published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        return course

    def list_courses(self, status_filter: Optional[CourseStatus] = None) -> list[Course]:
        """List courses with optional status filter."""
        if status_filter is not None:
            return self.course_repo.list_all(status_filter=status_filter)
        else:
            return self.course_repo.list_published()

    def update_course(
        self,
        course_id: uuid.UUID,
        user: User,
        **update_data,
    ) -> Course:
        """Update course with authorization checks."""
        course = self.get_course(course_id, public=False)

        # Check authorization
        role_names = [r.name for r in (user.roles or [])]
        if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to update this course",
            )

        course = self.course_repo.update(course, **update_data)
        self.db.commit()
        self.db.refresh(course)
        return course

    def delete_course(self, course_id: uuid.UUID, user: User) -> None:
        """Delete course with authorization checks."""
        course = self.get_course(course_id, public=False)

        # Check authorization
        role_names = [r.name for r in (user.roles or [])]
        if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to delete this course",
            )

        self.course_repo.delete(course)
        self.db.commit()

    async def publish_course(self, course_id: uuid.UUID, user: User) -> Course:
        """Publish a course and start Temporal workflow for AI processing."""
        from app.workflows.temporal_utils import start_publish_course_workflow
        
        course = self.get_course(course_id, public=False)

        # Check authorization
        role_names = [r.name for r in (user.roles or [])]
        if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to publish this course",
            )

        logger.info("user requested publish", course_id=str(course_id), user_id=str(user.id))

        # Validation: must have at least 1 module
        if not course.modules or len(course.modules) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course must have at least one module to publish",
            )

        # Idempotent: if already published, just return
        if course.status == CourseStatus.published:
            return course

        # Don't change status here - let the workflow handle it!
        # Just prepare course data for the workflow

        # Collect course data for AI service
        course_data = {
            "course_id": str(course.id),
            "title": course.title,
            "description": course.description,
            "instructor_id": str(course.instructor_id) if course.instructor_id else None,
            "assets": []
        }
        
        # Collect all assets from all modules
        for module in course.modules:
            for asset in module.assets:
                course_data["assets"].append({
                    "id": str(asset.id),
                    "title": asset.title,
                    "asset_type": asset.asset_type.value,
                    "source_url": asset.source_url,
                    "module_id": str(module.id),
                    "module_title": module.title
                })

        # Start Temporal workflow - it will handle ALL status changes
        try:
            workflow_result = await start_publish_course_workflow(
                course_id=course.id,
                course_data=course_data
            )
            logger.info(
                "Started Temporal workflow for course publishing",
                workflow_id=workflow_result["workflow_id"],
                course_id=str(course_id),
                asset_count=len(course_data["assets"])
            )
            
            # Refresh course to get updated status from workflow's first activity
            self.db.refresh(course)
            return course
            
        except Exception as e:
            logger.error(f"Failed to start Temporal workflow: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start workflow: {str(e)}"
            )
        
        return course

    def add_prerequisite(
        self,
        course_id: uuid.UUID,
        prerequisite_id: uuid.UUID,
        user: User,
    ) -> Course:
        """Add a prerequisite to a course (instructor/admin only)."""
        course = self.get_course(course_id, public=False)

        # Check authorization
        role_names = [r.name for r in (user.roles or [])]
        if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to modify this course",
            )

        # Prevent self-reference
        if course_id == prerequisite_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A course cannot be a prerequisite of itself",
            )

        # Verify prerequisite course exists
        prerequisite = self.course_repo.get_by_id(prerequisite_id)
        if not prerequisite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prerequisite course not found",
            )

        # Check if already added (idempotent)
        if prerequisite in course.prerequisites:
            return course

        # Add prerequisite
        course.prerequisites.append(prerequisite)
        self.db.commit()
        self.db.refresh(course)

        logger.info(
            "added prerequisite",
            course_id=str(course_id),
            prerequisite_id=str(prerequisite_id),
        )
        return course

    def remove_prerequisite(
        self,
        course_id: uuid.UUID,
        prerequisite_id: uuid.UUID,
        user: User,
    ) -> None:
        """Remove a prerequisite from a course (instructor/admin only)."""
        course = self.get_course(course_id, public=False)

        # Check authorization
        role_names = [r.name for r in (user.roles or [])]
        if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to modify this course",
            )

        # Verify prerequisite course exists
        prerequisite = self.course_repo.get_by_id(prerequisite_id)
        if not prerequisite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prerequisite course not found",
            )

        # Remove if present (idempotent)
        if prerequisite in course.prerequisites:
            course.prerequisites.remove(prerequisite)
            self.db.commit()

            logger.info(
                "removed prerequisite",
                course_id=str(course_id),
                prerequisite_id=str(prerequisite_id),
            )

    def list_prerequisites(self, course_id: uuid.UUID) -> list[Course]:
        """List all prerequisites for a course."""
        course = self.get_course(course_id, public=True)
        return course.prerequisites

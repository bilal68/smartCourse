# app/modules/courses/routes.py
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_db, get_current_active_user
from app.modules.auth.models import User
from app.modules.courses.models import CourseStatus
from app.modules.courses.service import CourseService
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post(
    "",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Create a new course."""
    course_service = CourseService(db)
    course = course_service.create_course(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        instructor_id=payload.instructor_id,
        user=user,
    )
    return course


@router.get("", response_model=List[CourseRead])
def list_courses(
    db: Session = Depends(get_db),
    status_filter: Optional[CourseStatus] = Query(
        default=None,
        description="Optional filter by course status",
    ),
):
    """List courses (published by default, or filtered by status)."""
    course_service = CourseService(db)
    courses = course_service.list_courses(status_filter=status_filter)
    return courses


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: UUID, db: Session = Depends(get_db)):
    """Get a course by ID (only published courses visible)."""
    course_service = CourseService(db)
    course = course_service.get_course(course_id, public=True)
    return course


@router.patch("/{course_id}", response_model=CourseRead)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Update a course."""
    course_service = CourseService(db)
    update_data = payload.model_dump(exclude_unset=True)
    course = course_service.update_course(course_id, user, **update_data)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Delete a course."""
    course_service = CourseService(db)
    course_service.delete_course(course_id, user)
    return None


@router.post("/{course_id}/publish", response_model=CourseRead)
async def publish_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Publish a course and emit an outbox event."""
    course_service = CourseService(db)
    course = await course_service.publish_course(course_id, user)
    return course


@router.post(
    "/{course_id}/prerequisites/{prerequisite_id}",
    response_model=CourseRead,
    status_code=status.HTTP_200_OK,
)
def add_prerequisite(
    course_id: UUID,
    prerequisite_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Add a prerequisite to a course (instructor/admin only)."""
    course_service = CourseService(db)
    course = course_service.add_prerequisite(course_id, prerequisite_id, user)
    return course


@router.delete(
    "/{course_id}/prerequisites/{prerequisite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_prerequisite(
    course_id: UUID,
    prerequisite_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Remove a prerequisite from a course (instructor/admin only)."""
    course_service = CourseService(db)
    course_service.remove_prerequisite(course_id, prerequisite_id, user)
    return None


@router.get("/{course_id}/prerequisites", response_model=List[CourseRead])
def list_prerequisites(
    course_id: UUID,
    db: Session = Depends(get_db),
):
    """List all prerequisites for a course."""
    course_service = CourseService(db)
    prerequisites = course_service.list_prerequisites(course_id)
    return prerequisites

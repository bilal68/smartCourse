# app/modules/enrollments/routes.py
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.deps import get_current_active_user, get_db
from app.modules.auth.models import User
from app.modules.enrollments.models import EnrollmentStatus
from app.modules.enrollments.service import EnrollmentService
from app.modules.courses.repository import CourseRepository
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentUpdate,
)

router = APIRouter(
    prefix="/enrollments",
    tags=["enrollments"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post(
    "",
    response_model=EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new enrollment."""
    enrollment_service = EnrollmentService(db)
    
    # If user_id not provided, default to current user (students enroll themselves)
    user_id = payload.user_id if payload.user_id else current_user.id
    
    enrollment = enrollment_service.create_enrollment(
        user_id=user_id,
        course_id=payload.course_id,
        status=payload.status,
        source=payload.source,
        current_user=current_user,
    )
    return enrollment


@router.get(
    "/me",
    response_model=List[EnrollmentRead],
)
def list_my_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's enrollments."""
    enrollment_service = EnrollmentService(db)
    enrollments = enrollment_service.list_enrollments_by_user(current_user.id)
    return enrollments


@router.get(
    "/by-user/{user_id}",
    response_model=List[EnrollmentRead],
)
def list_enrollments_by_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin-only: view any user's enrollments."""
    role_names = [r.name for r in (current_user.roles or [])]
    if "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view other users' enrollments",
        )

    enrollment_service = EnrollmentService(db)
    enrollments = enrollment_service.list_enrollments_by_user(user_id)
    return enrollments


@router.get(
    "/{enrollment_id}",
    response_model=EnrollmentRead,
)
def get_enrollment(
    enrollment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get enrollment by ID."""
    enrollment_service = EnrollmentService(db)
    enrollment = enrollment_service.get_enrollment(enrollment_id)

    # Permission: allow owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if (
        current_user.id != enrollment.user_id
        and current_user.id != enrollment.course.instructor_id
        and "admin" not in role_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this enrollment",
        )
    return enrollment


@router.get(
    "/by-course/{course_id}",
    response_model=List[EnrollmentRead],
)
def list_enrollments_by_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all enrollments for a course (instructor or admin only)."""
    # Permission: allow course instructor or admin
    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    role_names = [r.name for r in (current_user.roles or [])]
    if current_user.id != course.instructor_id and "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors and admins can view enrollments",
        )

    enrollment_service = EnrollmentService(db)
    enrollments = enrollment_service.list_enrollments_by_course(course_id)
    return enrollments


@router.patch(
    "/{enrollment_id}",
    response_model=EnrollmentRead,
)
def update_enrollment(
    enrollment_id: UUID,
    payload: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an enrollment."""
    enrollment_service = EnrollmentService(db)
    enrollment = enrollment_service.get_enrollment(enrollment_id)

    # Permission: allow owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if (
        current_user.id != enrollment.user_id
        and current_user.id != enrollment.course.instructor_id
        and "admin" not in role_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this enrollment",
        )

    data = payload.model_dump(exclude_unset=True)

    # if status is changed to completed, set completed_at if not set
    new_status = data.get("status")
    if new_status is not None:
        if new_status == EnrollmentStatus.completed and enrollment.completed_at is None:
            data["completed_at"] = func.now()

    enrollment = enrollment_service.update_enrollment(enrollment_id, current_user, **data)
    return enrollment


@router.delete(
    "/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_enrollment(
    enrollment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete an enrollment."""
    enrollment_service = EnrollmentService(db)
    enrollment = enrollment_service.get_enrollment(enrollment_id)

    # Permission: allow owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if (
        current_user.id != enrollment.user_id
        and current_user.id != enrollment.course.instructor_id
        and "admin" not in role_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this enrollment",
        )

    enrollment_service.delete_enrollment(enrollment_id, current_user)
    return None

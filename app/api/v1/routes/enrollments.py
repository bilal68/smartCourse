from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_current_active_user, get_db
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User
from app.models.course import Course
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentUpdate,
)
from app.tasks.enrollment_tasks import handle_enrollment_post_actions
from datetime import datetime
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/enrollments", tags=["enrollments"], dependencies=[Depends(get_current_active_user)])


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
    # Permission: students can only enroll themselves; instructors/admins can enroll others
    role_names = [r.name for r in (current_user.roles or [])]
    if current_user.id != payload.user_id and "instructor" not in role_names and "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only enroll yourself; instructors/admins can enroll others",
        )

    # 1) ensure user exists
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 2) ensure course exists
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # 3) idempotency: check if already enrolled
    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == payload.user_id,
            Enrollment.course_id == payload.course_id,
        )
        .first()
    )
    if existing:
        return existing

    enrollment = Enrollment(
        user_id=payload.user_id,
        course_id=payload.course_id,
        status=payload.status,
        source=payload.source,
    )
    # kafka event for enrollment created
    outbox = OutboxEvent(
        event_type="enrollment.created",
        aggregate_type="enrollment",
        aggregate_id=enrollment.id,  # works because UUID default is set on object creation
        payload={
            "enrollment_id": str(enrollment.id),
            "user_id": str(enrollment.user_id),
            "course_id": str(enrollment.course_id),
            "status": enrollment.status.value if hasattr(enrollment.status, "value") else str(enrollment.status),
            "source": enrollment.source,
            "enrolled_at": datetime.utcnow().isoformat(),
        },
        status=OutboxStatus.pending,
        attempts=0,
    )
    db.add(enrollment)
    db.add(outbox)
    db.commit()
    db.refresh(enrollment)
    logger.info("created enrollment", enrollment_id=str(enrollment.id), user_id=str(enrollment.user_id), course_id=str(enrollment.course_id))
    handle_enrollment_post_actions.delay(str(enrollment.id))
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
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
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
    
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
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
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )
    # Permission: allow owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if (current_user.id != enrollment.user_id and 
        current_user.id != enrollment.course.instructor_id and 
        "admin" not in role_names):
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
    # Permission: allow course instructor or admin
    course = db.query(Course).filter(Course.id == course_id).first()
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
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
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
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    # Permission: allow owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if (current_user.id != enrollment.user_id and 
        current_user.id != enrollment.course.instructor_id and 
        "admin" not in role_names):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this enrollment",
        )

    data = payload.model_dump(exclude_unset=True)

    # if status is changed to completed, set completed_at if not set
    new_status = data.get("status")
    if new_status is not None:
        enrollment.status = new_status
        if new_status == EnrollmentStatus.completed and enrollment.completed_at is None:
            from sqlalchemy import func

            # let DB clock set completed_at
            enrollment.completed_at = func.now()

    db.commit()
    db.refresh(enrollment)
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
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    # Permission: allow owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if (current_user.id != enrollment.user_id and 
        current_user.id != enrollment.course.instructor_id and 
        "admin" not in role_names):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this enrollment",
        )

    db.delete(enrollment)
    db.commit()
    return None

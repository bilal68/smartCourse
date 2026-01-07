from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
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
):
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
    db.commit()
    db.refresh(enrollment)
    logger.info("created enrollment", enrollment_id=str(enrollment.id), user_id=str(enrollment.user_id), course_id=str(enrollment.course_id))
    handle_enrollment_post_actions.delay(str(enrollment.id))
    return enrollment


@router.get(
    "/{enrollment_id}",
    response_model=EnrollmentRead,
)
def get_enrollment(
    enrollment_id: UUID,
    db: Session = Depends(get_db),
):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )
    return enrollment


@router.get(
    "/by-user/{user_id}",
    response_model=List[EnrollmentRead],
)
def list_enrollments_by_user(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    return enrollments


@router.get(
    "/by-course/{course_id}",
    response_model=List[EnrollmentRead],
)
def list_enrollments_by_course(
    course_id: UUID,
    db: Session = Depends(get_db),
):
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
):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
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
):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    db.delete(enrollment)
    db.commit()
    return None

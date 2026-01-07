from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_db, get_current_active_user
from app.models.course import Course, CourseStatus
from app.models.user import User
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.models.outbox_event import OutboxEvent, OutboxStatus
from datetime import datetime
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post(
    "",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    # Only users with the 'instructor' role (or 'admin') may create courses
    role_names = [r.name for r in (user.roles or [])]
    if "instructor" not in role_names and "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors or admins can create courses",
        )

    # If instructor_id is provided in payload, only admin may set it to another user
    if payload.instructor_id:
        if "admin" not in role_names and payload.instructor_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You may not set instructor_id for other users",
            )
        instructor_id = payload.instructor_id
    else:
        # default to the authenticated instructor
        instructor_id = user.id if "instructor" in role_names else None

    course = Course(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        instructor_id=instructor_id,
    )

    db.add(course)
    db.commit()
    db.refresh(course)
    logger.info("created course", course_id=str(course.id), title=course.title)
    return course


@router.get("", response_model=List[CourseRead])
def list_courses(
    db: Session = Depends(get_db),
    status_filter: Optional[CourseStatus] = Query(
        default=None,
        description="Optional filter by course status",
    ),
):
    query = db.query(Course)

    # apply explicit filter when provided, otherwise return published courses
    if status_filter is not None:
        query = query.filter(Course.status == status_filter)
    else:
        query = query.filter(Course.status == CourseStatus.published)

    courses = query.order_by(Course.created_at.desc()).all()
    return courses


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: UUID, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # unpublished courses are not visible via the public GET
    if course.status != CourseStatus.published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    return course


@router.patch("/{course_id}", response_model=CourseRead)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    role_names = [r.name for r in (user.roles or [])]
    if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to update this course")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    role_names = [r.name for r in (user.roles or [])]
    if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to delete this course")

    db.delete(course)
    db.commit()
    return None

@router.post("/{course_id}/publish", response_model=CourseRead)
def publish_course(course_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # Optional: allow only instructor owner or admin
    # Adjust this check to match your role system
    role_names = [r.name for r in (user.roles or [])]
    if course.instructor_id and course.instructor_id != user.id and "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to publish this course",
        )

    logger.info("user requested publish", course_id=str(course_id), user_id=str(user.id))

    # Optional rule: must have at least 1 module to publish
    if not course.modules or len(course.modules) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course must have at least one module to publish",
        )

    # Idempotent: if already published, just return
    if course.status == CourseStatus.published:
        return course

    course.status = CourseStatus.published

    outbox = OutboxEvent(
        event_type="course.published",
        aggregate_type="course",
        aggregate_id=course.id,
        payload={
            "course_id": str(course.id),
            "title": course.title,
            "description": course.description,
            "instructor_id": str(course.instructor_id) if course.instructor_id else None,
            "published_at": datetime.utcnow().isoformat(),
        },
        status=OutboxStatus.pending,
        attempts=0,
    )

    db.add(outbox)
    db.commit()
    db.refresh(course)
    logger.info("created outbox event", outbox_id=str(outbox.id), event_type=outbox.event_type)
    return course

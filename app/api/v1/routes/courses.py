from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_db, get_current_active_user
from app.models.course import Course, CourseStatus
from app.models.user import User
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate

router = APIRouter(
    prefix="/courses", tags=["courses"], dependencies=[Depends(get_current_active_user)]
)


@router.post(
    "",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    course = Course(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        instructor_id=payload.instructor_id,
    )

    db.add(course)
    db.commit()
    db.refresh(course)
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
    if status_filter is not None:
        query = query.filter(Course.status == status_filter)
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
    return course


@router.patch("/{course_id}", response_model=CourseRead)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: UUID, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    db.delete(course)
    db.commit()
    return None

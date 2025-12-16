from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.course import CourseStatus


class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.draft


class CourseCreate(CourseBase):
    # optional for now; later we can take from the authenticated user
    instructor_id: Optional[UUID] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CourseStatus] = None
    instructor_id: Optional[UUID] = None


class CourseRead(CourseBase):
    id: UUID
    instructor_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

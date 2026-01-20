from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.modules.courses.models import CourseStatus


class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None


class CourseCreate(CourseBase):
    # Status is always set to draft on creation - user cannot override
    # Courses progress through draft → published lifecycle via publish endpoint
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CourseStatus] = None
    # instructor_id cannot be changed after creation - it's set from authenticated user


class CourseRead(CourseBase):
    id: UUID
    status: CourseStatus
    instructor_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

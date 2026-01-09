from uuid import UUID
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.enrollments.models import EnrollmentStatus


class EnrollmentBase(BaseModel):
    status: EnrollmentStatus = EnrollmentStatus.active
    source: Optional[str] = None


class EnrollmentCreate(EnrollmentBase):
    user_id: UUID 
    course_id: UUID


class EnrollmentUpdate(BaseModel):
    status: Optional[EnrollmentStatus] = None


class EnrollmentRead(EnrollmentBase):
    id: UUID
    user_id: UUID
    course_id: UUID
    enrolled_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

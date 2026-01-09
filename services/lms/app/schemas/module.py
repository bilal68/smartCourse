from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ModuleBase(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 1


class ModuleCreate(ModuleBase):
    course_id: UUID


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None


class ModuleRead(ModuleBase):
    id: UUID
    course_id: UUID

    model_config = ConfigDict(from_attributes=True)

from uuid import UUID
from typing import Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssetProgressBase(BaseModel):
    percent_complete: float
    source: Optional[str] = None
    last_state: Optional[dict[str, Any]] = None


class AssetProgressCreate(AssetProgressBase):
    enrollment_id: UUID


class AssetProgressRead(AssetProgressBase):
    id: UUID
    asset_id: UUID
    enrollment_id: UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CourseProgressRead(BaseModel):
    id: UUID
    enrollment_id: UUID
    percent_complete: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assets: List[AssetProgressRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

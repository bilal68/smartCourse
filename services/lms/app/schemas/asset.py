# app/schemas/asset.py
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, HttpUrl, ConfigDict

from app.modules.courses.models import AssetType


class LearningAssetBase(BaseModel):
    title: str
    description: Optional[str] = None
    asset_type: AssetType = AssetType.other
    source_url: Optional[HttpUrl] = None
    order_index: int = 1
    duration_seconds: Optional[int] = None


class LearningAssetCreate(LearningAssetBase):
    module_id: UUID


class LearningAssetUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    asset_type: Optional[AssetType] = None
    source_url: Optional[HttpUrl] = None
    order_index: Optional[int] = None
    duration_seconds: Optional[int] = None


class LearningAssetRead(LearningAssetBase):
    id: UUID
    module_id: UUID

    model_config = ConfigDict(from_attributes=True)

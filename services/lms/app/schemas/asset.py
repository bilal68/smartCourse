# app/schemas/asset.py
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, HttpUrl, ConfigDict

from app.modules.courses.models import AssetType, AssetStatus


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


class UploadUrlRequest(BaseModel):
    """Request to initiate content upload"""
    content_type: str = "application/json"
    size_bytes: int


class UploadUrlResponse(BaseModel):
    """Response with signed PUT URL"""
    asset_id: UUID
    upload_url: str
    expires_in: int
    required_headers: dict = {"Content-Type": "application/json"}


class CompleteUploadResponse(BaseModel):
    """Response after upload validation"""
    id: UUID
    status: AssetStatus
    size_bytes: Optional[int] = None
    content_hash: Optional[str] = None
    version: int = 1
    validation_error: Optional[str] = None
    message: str


class LearningAssetRead(LearningAssetBase):
    id: UUID
    module_id: UUID
    status: AssetStatus = AssetStatus.draft
    content_format: str = "EDITOR_JSON"
    storage_provider: str = "S3"
    size_bytes: Optional[int] = None
    version: int = 1

    model_config = ConfigDict(from_attributes=True)


class AssetContentResponse(BaseModel):
    """Response with signed GET URL for reading content"""
    id: UUID
    title: str
    description: Optional[str] = None
    asset_type: AssetType
    content_format: str
    content_url: str  # Signed GET URL
    expires_in: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

# app/modules/courses/upload_routes.py
"""Article content upload and management endpoints using S3-compatible storage"""

import hashlib
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.content_constants import (
    GET_EXPIRY_SECONDS,
    MAX_ARTICLE_JSON_SIZE,
    UPLOAD_EXPIRY_SECONDS,
)
from app.db.deps import get_current_active_user, get_db
from app.modules.courses.models import LearningAsset, Module, AssetStatus, AssetType
from app.modules.auth.models import User
from app.schemas.asset import (
    UploadUrlRequest,
    UploadUrlResponse,
    CompleteUploadResponse,
    AssetContentResponse,
)
from app.storage.s3_client import get_s3_client
from app.modules.courses.validators import validate_editor_json
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/assets",
    tags=["upload"],
    dependencies=[Depends(get_current_active_user)]
)


@router.post(
    "/{asset_id}/content/upload-url",
    response_model=UploadUrlResponse,
    status_code=status.HTTP_200_OK,
)
def initiate_upload(
    asset_id: UUID,
    payload: UploadUrlRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Initiate article content upload - generate presigned PUT URL
    
    Flow:
    1. Validate asset ownership (instructor owns course)
    2. Check asset type is ARTICLE
    3. Validate file size <= 2MB
    4. Generate S3 key and presigned PUT URL (http:// or https://)
    5. Update asset status to UPLOAD_PENDING
    6. Return presigned URL to frontend/Postman
    
    Frontend must:
    - PUT binary content to the presigned URL
    - Include Content-Type header (as specified in response)
    - Then call POST /complete to validate
    """
    
    # Get asset with module and course
    asset = (
        db.query(LearningAsset)
        .join(Module)
        .filter(LearningAsset.id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Verify instructor owns the course
    module = asset.module
    course = module.course
    
    if course.instructor_id != current_user.id:
        logger.warning(
            f"Unauthorized upload attempt",
            extra={"user_id": str(current_user.id), "asset_id": str(asset_id)}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload content for this asset",
        )

    # Verify asset type is ARTICLE
    if asset.asset_type != AssetType.article:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset type must be ARTICLE, got {asset.asset_type.value}",
        )

    # Validate file size
    if payload.size_bytes > MAX_ARTICLE_JSON_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
            detail=f"File size {payload.size_bytes} bytes exceeds maximum {MAX_ARTICLE_JSON_SIZE} bytes",
        )

    # Build S3 key using forward slashes
    s3_client = get_s3_client()
    s3_key = s3_client.build_asset_key(course.id, module.id, asset.id)

    # Generate presigned PUT URL (no await needed - synchronous)
    try:
        upload_url = s3_client.presign_put(
            key=s3_key,
            content_type=payload.content_type,
            expires_in=UPLOAD_EXPIRY_SECONDS,
        )
        logger.info(f"Generated presigned PUT URL: key={s3_key}, expires_in={UPLOAD_EXPIRY_SECONDS}s")
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )

    # Update asset in DB
    asset.status = AssetStatus.upload_pending
    asset.bucket = s3_client.bucket
    asset.key = s3_key
    asset.expected_content_type = payload.content_type
    asset.size_bytes = payload.size_bytes
    asset.validation_error = None

    db.add(asset)
    db.commit()
    db.refresh(asset)

    logger.info(
        f"Upload initiated",
        extra={
            "asset_id": str(asset.id),
            "key": s3_key,
            "size_bytes": payload.size_bytes,
        }
    )

    return UploadUrlResponse(
        asset_id=asset.id,
        upload_url=upload_url,
        expires_in=UPLOAD_EXPIRY_SECONDS,
        required_headers={"Content-Type": payload.content_type},
    )


@router.post(
    "/{asset_id}/content/complete",
    response_model=CompleteUploadResponse,
    status_code=status.HTTP_200_OK,
)
def complete_upload(
    asset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Complete upload and validate content
    
    Flow:
    1. Get asset from DB
    2. Verify instructor ownership
    3. Fetch object from S3 (HEAD + GET)
    4. Validate JSON schema
    5. Compute SHA256 hash
    6. Update asset status to READY or REJECTED
    """
    
    # Get asset with relationships
    asset = (
        db.query(LearningAsset)
        .join(Module)
        .filter(LearningAsset.id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Verify instructor owns course
    course = asset.module.course
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to validate this asset",
        )

    # Verify asset is in UPLOAD_PENDING state
    if asset.status != AssetStatus.upload_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset status must be UPLOAD_PENDING, got {asset.status.value}",
        )

    # Verify bucket and key are set
    if not asset.bucket or not asset.key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset storage location not configured",
        )

    s3_client = get_s3_client()

    # ===== STEP 1: Check if object exists in S3 =====
    try:
        exists = s3_client.object_exists(asset.key)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content file not found in storage. Please re-upload.",
            )
    except Exception as e:
        logger.error(f"Failed to check object existence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify upload",
        )

    # ===== STEP 2: Get object metadata =====
    try:
        metadata = s3_client.head_object(asset.key)
        actual_size = metadata.get("ContentLength", metadata.get("Size"))

        # Verify size is reasonable
        if actual_size > MAX_ARTICLE_JSON_SIZE:
            asset.status = AssetStatus.rejected
            asset.validation_error = f"File too large: {actual_size} bytes (max {MAX_ARTICLE_JSON_SIZE})"
            db.add(asset)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
                detail=asset.validation_error,
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Failed to get object metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify file",
        )

    # ===== STEP 3: Download and parse JSON =====
    try:
        content_bytes = s3_client.get_object_bytes(asset.key)
    except Exception as e:
        logger.error(f"Failed to download content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download content for validation",
        )

    # Try to parse JSON
    try:
        json_data = json.loads(content_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        asset.status = AssetStatus.rejected
        asset.validation_error = f"Invalid JSON: {str(e)}"
        db.add(asset)
        db.commit()

        logger.warning(
            f"JSON parse error",
            extra={"asset_id": str(asset_id), "error": str(e)}
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON format: {str(e)}",
        )

    # ===== STEP 4: Validate schema =====
    is_valid, validation_errors = validate_editor_json(json_data)

    if not is_valid:
        error_msg = "; ".join(validation_errors)
        asset.status = AssetStatus.rejected
        asset.validation_error = error_msg
        db.add(asset)
        db.commit()

        logger.warning(
            f"Schema validation failed",
            extra={"asset_id": str(asset_id), "errors": validation_errors}
        )

        # Return 400 with validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content validation failed: {error_msg}",
        )

    # ===== STEP 5: Compute hash =====
    content_hash = hashlib.sha256(content_bytes).hexdigest()

    # ===== STEP 6: Update asset to READY =====
    asset.status = AssetStatus.ready
    asset.size_bytes = actual_size
    asset.content_hash = content_hash
    asset.version = 1
    asset.validation_error = None

    db.add(asset)
    db.commit()
    db.refresh(asset)

    logger.info(
        f"Upload completed successfully",
        extra={
            "asset_id": str(asset_id),
            "size_bytes": actual_size,
            "hash": content_hash,
        }
    )

    return CompleteUploadResponse(
        id=asset.id,
        status=asset.status,
        size_bytes=asset.size_bytes,
        content_hash=asset.content_hash,
        version=asset.version,
        validation_error=None,
        message="Content uploaded and validated successfully!",
    )


@router.get(
    "/{asset_id}/content",
    response_model=AssetContentResponse,
    status_code=status.HTTP_200_OK,
)
def get_asset_content(
    asset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get asset content with presigned GET URL
    
    Flow:
    1. Verify student is enrolled in course (or instructor owns it)
    2. Verify asset status is READY
    3. Generate presigned GET URL (http:// or https://)
    4. Return metadata + content_url (presigned URL, not permanent)
    
    Frontend can:
    - GET from presigned URL to download content
    - URL expires after configured time (default 600s)
    """
    
    # Get asset
    asset = (
        db.query(LearningAsset)
        .filter(LearningAsset.id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Verify asset is READY
    if asset.status != AssetStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Content is not ready yet",
        )

    # TODO: Verify student is enrolled in course OR instructor owns it
    # For now, allow access if asset is ready
    # In production, check enrollment or instructor ownership

    # Generate presigned GET URL
    s3_client = get_s3_client()
    try:
        content_url = s3_client.presign_get(
            key=asset.key,
            expires_in=GET_EXPIRY_SECONDS,
        )
        logger.info(f"Generated presigned GET URL for asset_id={asset_id}")
    except Exception as e:
        logger.error(f"Failed to generate GET URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download link",
        )

    return AssetContentResponse(
        id=asset.id,
        title=asset.title,
        description=asset.description,
        asset_type=asset.asset_type,
        content_format=asset.content_format,
        content_url=content_url,
        expires_in=GET_EXPIRY_SECONDS,
        created_at=asset.created_at.isoformat(),
        updated_at=asset.updated_at.isoformat(),
    )

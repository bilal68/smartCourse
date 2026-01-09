# app/api/v1/routes/assets.py
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_current_active_user, get_db
from app.modules.courses.models import LearningAsset, Module
from app.schemas.asset import (
    LearningAssetCreate,
    LearningAssetRead,
    LearningAssetUpdate,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"], dependencies=[Depends(get_current_active_user)])


@router.post(
    "",
    response_model=LearningAssetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset(payload: LearningAssetCreate, db: Session = Depends(get_db)):
    # ensure module exists
    module = db.query(Module).filter(Module.id == payload.module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    asset = LearningAsset(
        module_id=payload.module_id,
        title=payload.title,
        description=payload.description,
        asset_type=payload.asset_type,
        source_url=str(payload.source_url) if payload.source_url else None,
        order_index=payload.order_index,
        duration_seconds=payload.duration_seconds,
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)
    logger.info("created asset", asset_id=str(asset.id), module_id=str(asset.module_id))
    return asset


@router.get(
    "/by-module/{module_id}",
    response_model=List[LearningAssetRead],
)
def list_assets_by_module(module_id: UUID, db: Session = Depends(get_db)):
    assets = (
        db.query(LearningAsset)
        .filter(LearningAsset.module_id == module_id)
        .order_by(LearningAsset.order_index)
        .all()
    )
    return assets


@router.get(
    "/{asset_id}",
    response_model=LearningAssetRead,
)
def get_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = db.query(LearningAsset).filter(LearningAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )
    return asset


@router.patch(
    "/{asset_id}",
    response_model=LearningAssetRead,
)
def update_asset(
    asset_id: UUID,
    payload: LearningAssetUpdate,
    db: Session = Depends(get_db),
):
    asset = db.query(LearningAsset).filter(LearningAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    data = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        if field == "source_url" and value is not None:
            value = str(value)
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return asset


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = db.query(LearningAsset).filter(LearningAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    db.delete(asset)
    db.commit()
    return None

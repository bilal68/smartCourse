from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_current_active_user, get_db
from app.models.asset_progress import AssetProgress
from app.models.course_progress import CourseProgress
from app.models.user import User
from app.models.learning_asset import LearningAsset
from app.models.enrollment import Enrollment
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.schemas.progress import (
    AssetProgressCreate,
    AssetProgressRead,
    CourseProgressRead,
)
from app.core.logging import get_logger
from datetime import datetime

from app.tasks.progress_task import recalc_course_progress

logger = get_logger(__name__)

router = APIRouter(prefix="/progress", tags=["progress"], dependencies=[Depends(get_current_active_user)])


@router.post("/assets/{asset_id}", response_model=AssetProgressRead, status_code=status.HTTP_201_CREATED)
def upsert_asset_progress(
    asset_id: UUID,
    payload: AssetProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # permission: students may only update their own enrollment; instructors/admins can update others
    role_names = [r.name for r in (current_user.roles or [])]
    if current_user.id != payload.enrollment_id and "instructor" not in role_names and "admin" not in role_names:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this enrollment progress")

    asset = db.query(LearningAsset).filter(LearningAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    enrollment = db.query(Enrollment).filter(Enrollment.id == payload.enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    # upsert asset progress
    ap = (
        db.query(AssetProgress)
        .filter(AssetProgress.asset_id == asset_id, AssetProgress.enrollment_id == payload.enrollment_id)
        .first()
    )
    now = datetime.utcnow()
    if ap:
        ap.percent_complete = payload.percent_complete
        if ap.started_at is None and payload.percent_complete > 0:
            ap.started_at = now
        if payload.percent_complete >= 100.0 and ap.completed_at is None:
            ap.completed_at = now
    else:
        ap = AssetProgress(
            asset_id=asset_id,
            enrollment_id=payload.enrollment_id,
            percent_complete=payload.percent_complete,
            started_at=(now if payload.percent_complete > 0 else None),
            completed_at=(now if payload.percent_complete >= 100.0 else None),
        )
        db.add(ap)

    # persist outbox event for async aggregation/notifications
    outbox = OutboxEvent(
        event_type="asset.progress.updated",
        aggregate_type="asset_progress",
        aggregate_id=ap.id,
        payload={
            "asset_id": str(asset_id),
            "enrollment_id": str(payload.enrollment_id),
            "percent_complete": payload.percent_complete,
        },
        status=OutboxStatus.pending,
        attempts=0,
    )
    db.add(outbox)
    db.commit()
    db.refresh(ap)
    
    recalc_course_progress.delay(str(payload.enrollment_id))

    logger.info("asset progress upserted", asset_id=str(asset_id), enrollment_id=str(payload.enrollment_id), percent=ap.percent_complete)
    return ap


@router.get("/assets/{asset_id}", response_model=AssetProgressRead)
def get_asset_progress(asset_id: UUID, enrollment_id: UUID = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    ap = (
        db.query(AssetProgress)
        .filter(AssetProgress.asset_id == asset_id, AssetProgress.enrollment_id == enrollment_id)
        .first()
    )
    if not ap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset progress not found")

    # permission: owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if current_user.id != ap.enrollment_id and "admin" not in role_names and "instructor" not in role_names:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this progress")

    return ap


@router.get("/enrollments/{enrollment_id}", response_model=CourseProgressRead)
def get_course_progress(enrollment_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    # permission: owner, course instructor, or admin
    role_names = [r.name for r in (current_user.roles or [])]
    if current_user.id != enrollment.user_id and current_user.id != enrollment.course.instructor_id and "admin" not in role_names:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this progress")

    cp = db.query(CourseProgress).filter(CourseProgress.enrollment_id == enrollment_id).first()
    assets = (
        db.query(AssetProgress)
        .filter(AssetProgress.enrollment_id == enrollment_id)
        .order_by(AssetProgress.created_at)
        .all()
    )
    if not cp:
        # return synthesized response with 0% if missing
        from uuid import uuid4

        cp = CourseProgress(id=uuid4(), enrollment_id=enrollment_id, percent_complete=0.0, started_at=None, completed_at=None)

    # attach assets list for response
    cp.assets = assets
    return cp

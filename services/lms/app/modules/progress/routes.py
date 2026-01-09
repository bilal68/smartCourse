# app/modules/progress/routes.py
from uuid import UUID
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_current_active_user, get_db
from app.modules.auth.models import User
from app.modules.progress.models import AssetProgress, CourseProgress
from app.modules.progress.service import ProgressService
from app.modules.courses.repository import LearningAssetRepository
from app.modules.enrollments.repository import EnrollmentRepository
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.schemas.progress import (
    AssetProgressCreate,
    AssetProgressRead,
    CourseProgressRead,
)
from app.core.logging import get_logger
from app.tasks.progress_task import recalc_course_progress

logger = get_logger(__name__)

router = APIRouter(
    prefix="/progress",
    tags=["progress"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post(
    "/assets/{asset_id}",
    response_model=AssetProgressRead,
    status_code=status.HTTP_201_CREATED,
)
def upsert_asset_progress(
    asset_id: UUID,
    payload: AssetProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create or update asset progress."""
    # Permission: students may only update their own enrollment; instructors/admins can update others
    role_names = [r.name for r in (current_user.roles or [])]
    if (
        current_user.id != payload.enrollment_id
        and "instructor" not in role_names
        and "admin" not in role_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to update this enrollment progress",
        )

    # Validate asset exists
    asset_repo = LearningAssetRepository(db)
    asset = asset_repo.get_by_id(asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    # Validate enrollment exists
    enrollment_repo = EnrollmentRepository(db)
    enrollment = enrollment_repo.get_by_id(payload.enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found"
        )

    # Upsert asset progress
    progress_service = ProgressService(db)
    ap = progress_service.get_or_create_asset_progress(payload.enrollment_id, asset_id)

    now = datetime.utcnow()
    update_data = {"percent_complete": payload.percent_complete}
    
    if ap.started_at is None and payload.percent_complete > 0:
        update_data["started_at"] = now
    if payload.percent_complete >= 100.0 and ap.completed_at is None:
        update_data["completed_at"] = now

    progress_repo = progress_service.progress_repo
    ap = progress_repo.update_asset_progress(ap, **update_data)

    # Create outbox event for async aggregation/notifications
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

    # Trigger async course progress recalculation
    recalc_course_progress.delay(str(payload.enrollment_id))

    logger.info(
        "asset progress upserted",
        asset_id=str(asset_id),
        enrollment_id=str(payload.enrollment_id),
        percent=ap.percent_complete,
    )
    return ap


@router.get("/assets/{asset_id}", response_model=AssetProgressRead)
def get_asset_progress(
    asset_id: UUID,
    enrollment_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get asset progress for a specific enrollment."""
    progress_service = ProgressService(db)
    ap = progress_service.progress_repo.get_asset_progress(enrollment_id, asset_id)
    if not ap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset progress not found",
        )

    # Permission check
    enrollment_repo = EnrollmentRepository(db)
    enrollment = enrollment_repo.get_by_id(enrollment_id)
    role_names = [r.name for r in (current_user.roles or [])]
    if (
        current_user.id != enrollment.user_id
        and current_user.id != enrollment.course.instructor_id
        and "admin" not in role_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this progress",
        )

    return ap


@router.get("/enrollments/{enrollment_id}/assets", response_model=List[AssetProgressRead])
def list_asset_progress(
    enrollment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all asset progress for an enrollment."""
    enrollment_repo = EnrollmentRepository(db)
    enrollment = enrollment_repo.get_by_id(enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    # Permission check
    role_names = [r.name for r in (current_user.roles or [])]
    if (
        current_user.id != enrollment.user_id
        and current_user.id != enrollment.course.instructor_id
        and "admin" not in role_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this progress",
        )

    progress_service = ProgressService(db)
    asset_progress_list = progress_service.progress_repo.list_asset_progress_by_enrollment(
        enrollment_id
    )
    return asset_progress_list


@router.get("/enrollments/{enrollment_id}/course", response_model=CourseProgressRead)
def get_course_progress(
    enrollment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get course progress for an enrollment."""
    enrollment_repo = EnrollmentRepository(db)
    enrollment = enrollment_repo.get_by_id(enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    # Permission check
    role_names = [r.name for r in (current_user.roles or [])]
    if (
        current_user.id != enrollment.user_id
        and current_user.id != enrollment.course.instructor_id
        and "admin" not in role_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this progress",
        )

    progress_service = ProgressService(db)
    course_progress = progress_service.get_or_create_course_progress(enrollment_id)
    return course_progress

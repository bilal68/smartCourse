from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.progress.models import CourseProgress, AssetProgress
from app.modules.progress.repository import ProgressRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProgressService:
    """Service layer for progress tracking operations."""

    def __init__(self, db: Session):
        self.db = db
        self.progress_repo = ProgressRepository(db)

    def get_or_create_course_progress(
        self, enrollment_id: uuid.UUID
    ) -> CourseProgress:
        """Get or create course progress for an enrollment."""
        progress = self.progress_repo.get_course_progress(enrollment_id)
        if not progress:
            progress = self.progress_repo.create_course_progress(enrollment_id)
            self.db.commit()
            self.db.refresh(progress)
        return progress

    def get_or_create_asset_progress(
        self, enrollment_id: uuid.UUID, asset_id: uuid.UUID
    ) -> AssetProgress:
        """Get or create asset progress."""
        progress = self.progress_repo.get_asset_progress(enrollment_id, asset_id)
        if not progress:
            progress = self.progress_repo.create_asset_progress(enrollment_id, asset_id)
            self.db.commit()
            self.db.refresh(progress)
        return progress

    def update_asset_progress(
        self, enrollment_id: uuid.UUID, asset_id: uuid.UUID, percent_complete: float
    ) -> AssetProgress:
        """Update asset progress percentage."""
        progress = self.get_or_create_asset_progress(enrollment_id, asset_id)
        progress = self.progress_repo.update_asset_progress(
            progress, percent_complete=percent_complete
        )
        self.db.commit()
        self.db.refresh(progress)
        
        logger.info(
            "updated asset progress",
            enrollment_id=str(enrollment_id),
            asset_id=str(asset_id),
            percent_complete=percent_complete,
        )
        return progress

    def recalculate_course_progress(self, enrollment_id: uuid.UUID) -> CourseProgress:
        """Recalculate course progress based on asset progress."""
        # Get all asset progress for this enrollment
        asset_progress_list = self.progress_repo.list_asset_progress_by_enrollment(
            enrollment_id
        )

        # Calculate average completion
        if asset_progress_list:
            total_percent = sum(ap.percent_complete for ap in asset_progress_list)
            avg_percent = total_percent / len(asset_progress_list)
        else:
            avg_percent = 0.0

        # Update course progress
        course_progress = self.get_or_create_course_progress(enrollment_id)
        course_progress = self.progress_repo.update_course_progress(
            course_progress, percent_complete=avg_percent
        )
        self.db.commit()
        self.db.refresh(course_progress)

        logger.info(
            "recalculated course progress",
            enrollment_id=str(enrollment_id),
            percent_complete=avg_percent,
        )
        return course_progress

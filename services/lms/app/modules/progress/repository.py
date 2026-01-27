from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.progress.models import CourseProgress, AssetProgress


class ProgressRepository:
    """Repository for CourseProgress and AssetProgress entities."""

    def __init__(self, db: Session):
        self.db = db

    def get_course_progress(self, enrollment_id: uuid.UUID) -> Optional[CourseProgress]:
        """Get course progress by enrollment ID."""
        return (
            self.db.query(CourseProgress)
            .filter(CourseProgress.enrollment_id == enrollment_id)
            .first()
        )

    def get_asset_progress(
        self, enrollment_id: uuid.UUID, asset_id: uuid.UUID
    ) -> Optional[AssetProgress]:
        """Get asset progress by enrollment and asset ID."""
        return (
            self.db.query(AssetProgress)
            .filter(
                AssetProgress.enrollment_id == enrollment_id,
                AssetProgress.asset_id == asset_id,
            )
            .first()
        )

    def list_asset_progress_by_enrollment(
        self, enrollment_id: uuid.UUID
    ) -> list[AssetProgress]:
        """List all asset progress for an enrollment."""
        return (
            self.db.query(AssetProgress)
            .filter(AssetProgress.enrollment_id == enrollment_id)
            .all()
        )

    def create_course_progress(self, enrollment_id: uuid.UUID) -> CourseProgress:
        """Create course progress record."""
        progress = CourseProgress(enrollment_id=enrollment_id, percent_complete=0.0)
        self.db.add(progress)
        self.db.flush()
        return progress

    def create_asset_progress(
        self, enrollment_id: uuid.UUID, asset_id: uuid.UUID
    ) -> AssetProgress:
        """Create asset progress record."""
        progress = AssetProgress(
            enrollment_id=enrollment_id, asset_id=asset_id, percent_complete=0.0
        )
        self.db.add(progress)
        self.db.flush()
        return progress

    def update_course_progress(
        self, progress: CourseProgress, **kwargs
    ) -> CourseProgress:
        """Update course progress fields."""
        for key, value in kwargs.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        self.db.flush()
        return progress

    def update_asset_progress(self, progress: AssetProgress, **kwargs) -> AssetProgress:
        """Update asset progress fields."""
        for key, value in kwargs.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        self.db.flush()
        return progress

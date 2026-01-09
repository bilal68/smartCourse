from __future__ import annotations

from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.core.logging import get_logger

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.module import Module
from app.models.learning_asset import LearningAsset
from app.models.asset_progress import AssetProgress
from app.models.course_progress import CourseProgress
from app.models.certificate import Certificate

logger = get_logger(__name__)

MAX_RETRIES = 3


@celery_app.task(
    name="app.tasks.progress_tasks.recalc_course_progress",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": MAX_RETRIES},
)
def recalc_course_progress(self, enrollment_id: str) -> dict:
    db: Session = SessionLocal()
    try:
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            return {"ok": False, "reason": "enrollment_not_found"}

        # total assets in this course
        total_assets = (
            db.query(func.count(LearningAsset.id))
            .join(Module, Module.id == LearningAsset.module_id)
            .filter(Module.course_id == enrollment.course_id)
            .scalar()
        ) or 0

        # completed assets for this enrollment (>= 100%)
        completed_assets = (
            db.query(func.count(AssetProgress.id))
            .join(LearningAsset, LearningAsset.id == AssetProgress.asset_id)
            .join(Module, Module.id == LearningAsset.module_id)
            .filter(
                AssetProgress.enrollment_id == enrollment.id,
                Module.course_id == enrollment.course_id,
                AssetProgress.percent_complete >= 100.0,
            )
            .scalar()
        ) or 0

        percent = (
            0.0
            if total_assets == 0
            else round((completed_assets / total_assets) * 100.0, 2)
        )
        now = datetime.utcnow()

        cp = (
            db.query(CourseProgress)
            .filter(CourseProgress.enrollment_id == enrollment.id)
            .first()
        )
        if not cp:
            cp = CourseProgress(
                enrollment_id=enrollment.id,
                percent_complete=0.0,
                started_at=None,
                completed_at=None,
            )
            db.add(cp)

        became_complete_now = cp.completed_at is None and percent >= 100.0

        if percent > 0 and cp.started_at is None:
            cp.started_at = now

        cp.percent_complete = percent

        if became_complete_now:
            cp.completed_at = now
            enrollment.status = EnrollmentStatus.completed
            enrollment.completed_at = now

        db.commit()

        # trigger certificate async only once
        if became_complete_now:
            exists = (
                db.query(Certificate)
                .filter(Certificate.enrollment_id == enrollment.id)
                .first()
            )
            if not exists:
                from app.tasks.certificate_tasks import (
                    generate_certificate_for_enrollment,
                )

                generate_certificate_for_enrollment.delay(str(enrollment.id))

        logger.info(
            "recalc_course_progress done",
            enrollment_id=str(enrollment.id),
            percent=percent,
        )
        return {
            "ok": True,
            "percent": percent,
            "became_complete_now": became_complete_now,
        }
    finally:
        db.close()

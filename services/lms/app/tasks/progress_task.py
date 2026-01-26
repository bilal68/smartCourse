from __future__ import annotations

from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.core.logging import get_logger

from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from app.modules.courses.models import Module, LearningAsset
from app.modules.progress.models import AssetProgress, CourseProgress
from app.models.certificate import Certificate
from app.models.outbox_event import OutboxEvent, OutboxStatus

logger = get_logger(__name__)

MAX_RETRIES = 3


def recalc_course_progress_sync(db: Session, enrollment_id: str) -> OutboxEvent | None:
    """
    Synchronous course progress recalculation (database-first approach).
    
    This function:
    1. Recalculates course progress immediately (source of truth)
    2. Returns course completion outbox event if course became complete
    3. Does NOT trigger async tasks - everything is immediate for UX
    
    Returns OutboxEvent if course completion event should be emitted, None otherwise.
    """
    try:
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            logger.error(f"Enrollment not found: {enrollment_id}")
            return None

        # Calculate course progress based on asset completion
        total_assets = (
            db.query(func.count(LearningAsset.id))
            .join(Module, Module.id == LearningAsset.module_id)
            .filter(Module.course_id == enrollment.course_id)
            .scalar()
        ) or 0

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

        # Get or create course progress
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

        # Check if course is becoming complete for the first time
        became_complete_now = cp.completed_at is None and percent >= 100.0

        # Update course progress
        if percent > 0 and cp.started_at is None:
            cp.started_at = now
        cp.percent_complete = percent
        
        # Handle course completion
        course_completion_event = None
        if became_complete_now:
            cp.completed_at = now
            enrollment.status = EnrollmentStatus.completed
            enrollment.completed_at = now
            
            # Create course completion outbox event (to be added in same transaction)
            course_completion_event = OutboxEvent(
                event_type="course.progress.completed",
                aggregate_type="enrollment",
                aggregate_id=enrollment.id,
                payload={
                    "enrollment_id": str(enrollment.id),
                    "course_id": str(enrollment.course_id),
                    "user_id": str(enrollment.user_id),
                    "completion_date": now.isoformat(),
                    "final_percentage": 100.0,
                    "total_assets": total_assets,
                    "completed_assets": completed_assets,
                    "event_timestamp": now.isoformat()
                },
                status=OutboxStatus.pending,
                attempts=0
            )
            
            logger.info(f"Course completion detected for enrollment: {enrollment.id}")

        logger.info(
            "course progress recalculated synchronously",
            enrollment_id=str(enrollment.id),
            percent=percent,
            became_complete=became_complete_now,
        )
        
        return course_completion_event
        
    except Exception as e:
        logger.error(f"Failed to recalc course progress sync for {enrollment_id}: {str(e)}")
        raise


# ===== LEGACY ASYNC TASK - DEPRECATED =====
# Use recalc_course_progress_sync() instead for immediate consistency

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

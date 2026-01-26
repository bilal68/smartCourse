from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy.orm import Session, selectinload

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.core.logging import get_logger
from app.models.outbox_event import OutboxEvent
from app.modules.enrollments.models import Enrollment
from app.modules.courses.models import Course
from app.modules.auth.models import User

logger = get_logger(__name__)

@celery_app.task(
    name="app.tasks.enrollment_tasks.handle_enrollment_post_actions",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
)
def handle_enrollment_post_actions(self, enrollment_id: str):
    """
    Orchestrates all post-enrollment actions:
    1. Emit notification events (welcome email, etc.)
    2. Emit analytics events (enrollment tracking)
    3. Initialize progress tracking
    4. Log completion
    """
    db: Session = SessionLocal()
    try:
        # Load enrollment with relationships
        enrollment = (
            db.query(Enrollment)
            .options(
                selectinload(Enrollment.user),
                selectinload(Enrollment.course)
            )
            .filter(Enrollment.id == enrollment_id)
            .first()
        )
        
        if not enrollment:
            logger.error(f"Enrollment not found: {enrollment_id}")
            return {"status": "failed", "reason": "enrollment_not_found"}

        logger.info(f"Starting post-enrollment orchestration for enrollment: {enrollment_id}")
        
        # Emit single comprehensive enrollment event for all services
        emit_enrollment_completed_event(db, enrollment)
        
        # Initialize progress tracking (trigger separate task)
        initialize_progress_tracking.delay(str(enrollment.id))
        
        db.commit()
        logger.info(f"Post-enrollment orchestration completed for enrollment: {enrollment_id}")
        
        return {
            "status": "success", 
            "enrollment_id": enrollment_id,
            "actions_completed": ["event_emitted", "progress_init"]
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed post-enrollment actions for {enrollment_id}: {str(e)}")
        raise
    finally:
        db.close()


def emit_enrollment_completed_event(db: Session, enrollment: Enrollment):
    """
    Emit a single comprehensive enrollment event.
    
    This event will be consumed by:
    - Notification service: Send welcome email, access notifications
    - Analytics service: Track enrollment metrics, user activity
    """
    
    # Single comprehensive event with all data both services need
    enrollment_event = OutboxEvent(
        event_type="enrollment.completed",  # Domain event - what actually happened
        aggregate_type="enrollment",
        aggregate_id=enrollment.id,
        payload={
            # Core enrollment data
            "enrollment_id": str(enrollment.id),
            "user_id": str(enrollment.user_id), 
            "course_id": str(enrollment.course_id),
            "enrollment_status": enrollment.status.value,
            "enrollment_source": enrollment.source,
            "enrollment_date": enrollment.created_at.isoformat(),
            "event_timestamp": datetime.utcnow().isoformat(),
            
            # User data (for notifications)
            "user": {
                "full_name": enrollment.user.full_name,
                "email": enrollment.user.email,
                "signup_date": enrollment.user.created_at.isoformat() if enrollment.user.created_at else None
            },
            
            # Course data (for both services)
            "course": {
                "title": enrollment.course.title,
                "description": enrollment.course.description,
                "category": enrollment.course.category,
                "level": enrollment.course.level,
                "duration_hours": enrollment.course.duration_hours,
                "access_url": f"/courses/{enrollment.course_id}"
            },
            
            # Service hints (optional - services can decide what to do)
            "actions_suggested": {
                "notification": ["welcome_email", "access_granted"],
                "analytics": ["track_enrollment", "user_activity"]
            }
        }
    )
    
    db.add(enrollment_event)
    logger.info(f"Emitted enrollment.completed event for enrollment: {enrollment.id}")


@celery_app.task(
    name="app.tasks.enrollment_tasks.initialize_progress_tracking",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 3},
)
def initialize_progress_tracking(self, enrollment_id: str):
    """
    Initialize progress tracking for the enrolled course.
    This triggers the progress calculation task.
    """
    try:
        # Import here to avoid circular imports
        from app.tasks.progress_task import recalc_course_progress
        
        logger.info(f"Initializing progress tracking for enrollment: {enrollment_id}")
        
        # Trigger progress calculation
        result = recalc_course_progress.delay(enrollment_id)
        
        logger.info(f"Progress tracking initialized for enrollment: {enrollment_id}, task_id: {result.id}")
        
        return {
            "status": "success",
            "enrollment_id": enrollment_id,
            "progress_task_id": result.id
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize progress tracking for {enrollment_id}: {str(e)}")
        raise

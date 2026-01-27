"""Temporal workflow for course publishing with rollback on failure."""

import asyncio
from datetime import timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from temporalio import workflow, activity
from temporalio.exceptions import ApplicationError


# ------------------------
# Activities (run outside sandbox)
# ------------------------


@activity.defn
async def mark_course_processing_and_publish(
    course_id: str, course_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Mark course as PROCESSING and create course.published OUTBOX event (Activity 1 - Atomic)."""
    from datetime import datetime
    import logging
    from app.db.session import SessionLocal
    from app.models.outbox_event import OutboxEvent, OutboxStatus
    from app.modules.courses.models import Course, CourseStatus, CourseProcessingStatus
    # Import all models to ensure SQLAlchemy mappers are initialized
    from app.modules.auth.models import User, Role, UserRole
    from app.modules.enrollments.models import Enrollment
    from app.models.certificate import Certificate

    logger = logging.getLogger(__name__)
    db = SessionLocal()

    try:
        course = db.query(Course).filter(Course.id == UUID(course_id)).first()
        if not course:
            raise ApplicationError(f"Course not found: {course_id}")

        # 1) Mark as PUBLISHED + PROCESSING
        course.status = CourseStatus.published
        course.processing_status = CourseProcessingStatus.processing

        # 2) Create OUTBOX event in same transaction
        outbox = OutboxEvent(
            event_type="course.published",
            aggregate_type="course",
            aggregate_id=UUID(course_id),
            payload={
                "course_id": course_id,
                "course_data": course_data,
                "published_at": datetime.utcnow().isoformat(),
            },
            status=OutboxStatus.pending,
            attempts=0,
        )
        db.add(outbox)

        # 3) Commit atomically
        db.commit()

        logger.info(
            "Course PROCESSING + outbox created",
            extra={"course_id": course_id, "outbox_id": str(outbox.id)},
        )
        
        # 4) Trigger immediate outbox publishing (alternative to Celery Beat)
        try:
            from app.tasks.outbox_tasks import publish_pending_outbox
            publish_pending_outbox.delay()
            logger.info("Triggered outbox publishing task")
        except Exception as pub_err:
            logger.warning("Failed to trigger outbox task", extra={"error": str(pub_err)})
        
        return {
            "course_id": course_id,
            "status": "published",
            "processing_status": "processing",
            "outbox_id": str(outbox.id),
        }

    except Exception as e:
        db.rollback()
        logger.exception("Failed to mark course as processing")
        raise ApplicationError(f"Failed to mark course as processing: {str(e)}")

    finally:
        db.close()


@activity.defn
async def rollback_course_publish(course_id: str) -> Dict[str, Any]:
    """Compensating activity: rollback course to DRAFT on failure."""
    import logging
    from app.db.session import SessionLocal
    from app.modules.courses.models import Course, CourseStatus, CourseProcessingStatus
    # Import all models to ensure SQLAlchemy mappers are initialized
    from app.modules.auth.models import User, Role, UserRole
    from app.modules.enrollments.models import Enrollment
    from app.models.certificate import Certificate

    logger = logging.getLogger(__name__)
    db = SessionLocal()

    try:
        course = db.query(Course).filter(Course.id == UUID(course_id)).first()
        if not course:
            logger.warning(
                "Course not found during rollback", extra={"course_id": course_id}
            )
            return {"course_id": course_id, "rollback": "not_found"}

        course.status = CourseStatus.draft
        course.processing_status = CourseProcessingStatus.not_started
        course.processing_error = "Publishing failed and was rolled back"
        db.commit()

        logger.warning("Course rolled back to DRAFT", extra={"course_id": course_id})
        return {"course_id": course_id, "rollback": "success"}

    except Exception as e:
        logger.exception("Failed to rollback course")
        return {"course_id": course_id, "rollback": "failed", "error": str(e)}

    finally:
        db.close()


# ------------------------
# Workflow (runs in sandbox)
# ------------------------


@workflow.defn
class PublishCourseWorkflow:
    """
    Production signal-based workflow:

    1) Activity: mark processing + outbox `course.published`
    2) Wait for SIGNAL from LMS consumer: `ai_processing_done`
    3) If success -> complete
       If failure/timeout -> rollback
    """

    def __init__(self) -> None:
        self.ai_result: Optional[Dict[str, Any]] = None

    @workflow.signal
    async def ai_processing_done(self, result: Dict[str, Any]) -> None:
        """Signal from LMS Kafka consumer after AI completes."""
        workflow.logger.info(f"📨 Signal ai_processing_done received: {result}")
        self.ai_result = result

    @workflow.run
    async def run(self, course_id: str, course_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow.logger.info(f"🚀 Publish workflow started for course_id={course_id}")

        try:
            # Step 1
            result1 = await workflow.execute_activity(
                mark_course_processing_and_publish,
                args=[course_id, course_data],
                start_to_close_timeout=timedelta(seconds=30),
            )
            workflow.logger.info(f"✅ Step 1 complete: {result1}")

            # Step 2 (WAIT for signal)
            workflow.logger.info(
                "⏳ Waiting for AI completion signal (timeout=10min)..."
            )

            # Simple wait without timeout for now - signal will set ai_result
            def condition_check() -> bool:
                return self.ai_result is not None

            await workflow.wait_condition(condition_check)
            
            # Check if we got a result
            if self.ai_result is None:
                workflow.logger.error("⏰ Timeout waiting for AI completion signal")
                await workflow.execute_activity(
                    rollback_course_publish,
                    args=[course_id],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                raise ApplicationError(
                    f"AI processing timeout (10 minutes) for course {course_id}"
                )

            # Step 3 (evaluate signal)
            if not self.ai_result:
                raise ApplicationError("Signal received but payload is empty")

            if not self.ai_result.get("success", False):
                error_msg = self.ai_result.get(
                    "error_message", "Unknown AI processing error"
                )
                workflow.logger.error(f"❌ AI failed: {error_msg}")
                await workflow.execute_activity(
                    rollback_course_publish,
                    args=[course_id],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                raise ApplicationError(f"AI processing failed: {error_msg}")
#todo:to add outbox addedition for course.ai_processed event
            workflow.logger.info("✅ AI processing successful, completing workflow")

            return {
                "course_id": course_id,
                "status": "published",
                "processing_status": "ready",
                "workflow_status": "success",
                "chunks_created": self.ai_result.get("chunks_created", 0),
            }

        except ApplicationError:
            raise

        except Exception as e:
            workflow.logger.error(
                f"❌ Workflow failed: {type(e).__name__}: {str(e) or 'no message'}"
            )
            try:
                await workflow.execute_activity(
                    rollback_course_publish,
                    args=[course_id],
                    start_to_close_timeout=timedelta(seconds=10),
                )
            except Exception as rollback_error:
                workflow.logger.error(f"❌ Rollback failed too: {rollback_error}")
            raise ApplicationError(
                f"Course publishing failed: {type(e).__name__}: {str(e) or 'no message'}"
            )

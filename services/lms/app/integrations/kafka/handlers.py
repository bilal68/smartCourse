"""Event handlers for LMS Kafka consumer."""

from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import SessionLocal
from app.modules.courses.models import Course, CourseProcessingStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class LMSEventHandler:
    """Handles Kafka events for LMS service."""
    
    def handle_content_processed(self, event: Dict[str, Any]):
        """Handle content.processed event from AI service."""
        course_id = event.get("course_id")
        status = event.get("status")
        error_message = event.get("error_message")
        
        logger.info("Handling content processed event", course_id=course_id, status=status)
        
        db: Session = SessionLocal()
        try:
            # Get the course
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                logger.warning("Course not found for content processed event", course_id=course_id)
                return
            
            # Update processing status based on AI service response
            if status == "completed":
                course.processing_status = CourseProcessingStatus.ready
                course.processing_error = error_message  # May be None or partial error
            elif status == "failed":
                course.processing_status = CourseProcessingStatus.failed
                course.processing_error = error_message
            else:
                logger.warning("Unknown processing status", status=status)
                return
            
            course.processed_at = datetime.utcnow()
            
            # Note: Content chunks are now stored in AI service database
            # LMS no longer stores content chunks directly
            
            db.commit()
            
            logger.info(
                "Content processing status updated",
                course_id=course_id,
                status=course.processing_status.value,
                processed_assets=event.get("processed_assets", 0),
                total_chunks=event.get("total_chunks", 0)
            )
            
        except Exception as e:
            logger.error(
                "Failed to handle content processed event",
                course_id=course_id,
                error=str(e),
                exc_info=True
            )
            db.rollback()
        finally:
            db.close()


# Global handler instance
_lms_handler = None


def get_lms_event_handler() -> LMSEventHandler:
    """Get the global LMS event handler."""
    global _lms_handler
    if _lms_handler is None:
        _lms_handler = LMSEventHandler()
    return _lms_handler
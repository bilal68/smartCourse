"""
Kafka consumer for AI processing completion events.

This consumer listens for 'course.processing_completed' or 'course.processing_failed' events,
updates the course status in DB atomically with OUTBOX event creation,
then signals the corresponding Temporal workflow.
"""

import json
import asyncio
from typing import Dict, Any
from uuid import UUID

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.modules.courses.models import Course, CourseProcessingStatus
from app.workflows.temporal_utils import signal_ai_processing_done

# Import all models to ensure SQLAlchemy mappers are initialized
from app.modules.auth.models import User, Role, UserRole
from app.modules.enrollments.models import Enrollment
from app.models.certificate import Certificate

logger = get_logger(__name__)


def update_course_and_create_outbox(
    course_id: str,
    success: bool,
    chunks_created: int = 0,
    error_message: str = None
) -> Dict[str, Any]:
    """
    Update course status and create OUTBOX event in single atomic transaction.
    
    This replaces the old Activity #3 from the workflow - now done by Kafka consumer.
    """
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == UUID(course_id)).first()
        if not course:
            raise Exception(f"Course not found: {course_id}")
        
        if success:
            # Mark as READY
            course.processing_status = CourseProcessingStatus.ready
            from datetime import datetime
            course.processed_at = datetime.utcnow()
            
            # Create OUTBOX event for course.ready
            outbox = OutboxEvent(
                event_type="course.ready",
                aggregate_type="course",
                aggregate_id=UUID(course_id),
                payload={
                    "course_id": course_id,
                    "chunks_created": chunks_created,
                    "ready_at": datetime.utcnow().isoformat()
                },
                status=OutboxStatus.pending,
                attempts=0
            )
            db.add(outbox)
            logger.info(f"✅ Course marked as READY + course.ready OUTBOX created, course_id={course_id}")
            
        else:
            # Mark as FAILED
            course.processing_status = CourseProcessingStatus.failed
            course.processing_error = error_message or "AI processing failed"
            
            # Create OUTBOX event for course.processing_failed
            outbox = OutboxEvent(
                event_type="course.processing_failed",
                aggregate_type="course",
                aggregate_id=UUID(course_id),
                payload={
                    "course_id": course_id,
                    "error_message": error_message,
                    "failed_at": datetime.utcnow().isoformat()
                },
                status=OutboxStatus.pending,
                attempts=0
            )
            db.add(outbox)
            logger.error(f"❌ Course marked as FAILED, course_id={course_id}, error={error_message}")
        
        # Commit both changes atomically
        db.commit()
        
        return {
            "course_id": course_id,
            "success": success,
            "outbox_id": str(outbox.id)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update course and create outbox: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


async def process_ai_completion_event(message_value: bytes) -> None:
    """Process a single AI completion event from Kafka."""
    try:
        # Decode message
        payload = json.loads(message_value.decode("utf-8"))
        event_type = payload.get("event_type")
        course_id = payload.get("aggregate_id")
        event_payload = payload.get("payload", {})
        
        logger.info(f"📨 Received event: {event_type} for course_id={course_id}")
        
        # Determine success/failure
        if event_type == "course.processing_completed":
            success = True
            chunks_created = event_payload.get("total_chunks_created", 0)
            error_message = None
            
        elif event_type == "course.processing_failed":
            success = False
            chunks_created = 0
            error_message = event_payload.get("error_message", "Unknown error")
            
        else:
            logger.warning(f"Unknown event type: {event_type}, ignoring")
            return
        
        # Step 1: Update DB + Create OUTBOX atomically
        db_result = update_course_and_create_outbox(
            course_id=course_id,
            success=success,
            chunks_created=chunks_created,
            error_message=error_message
        )
        logger.info(f"✅ DB updated: {db_result}")
        
        # Step 2: Signal Temporal workflow
        signal_result = await signal_ai_processing_done(
            course_id=course_id,
            success=success,
            chunks_created=chunks_created,
            error_message=error_message
        )
        logger.info(f"✅ Workflow signaled: {signal_result}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode Kafka message: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to process AI completion event: {str(e)}", exc_info=True)


def run_ai_completion_consumer(bootstrap_servers: str = "localhost:9092"):
    """
    Run the Kafka consumer that listens for AI completion events.
    
    This should be run as a separate process/service.
    """
    consumer = None
    try:
        consumer = KafkaConsumer(
            "course.events",
            bootstrap_servers=[bootstrap_servers],
            group_id="lms-ai-completion-handler",  # Unique consumer group
            auto_offset_reset="latest",  # Only process new events
            enable_auto_commit=True,
            value_deserializer=lambda m: m  # Raw bytes, we'll decode manually
        )
        
        logger.info(f"🎧 AI Completion Consumer started, listening on 'course.events' topic...")
        
        for message in consumer:
            try:
                # Process event in async context
                asyncio.run(process_ai_completion_event(message.value))
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                continue
        
    except KafkaError as e:
        logger.error(f"Kafka consumer error: {str(e)}")
        raise
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    finally:
        if consumer:
            consumer.close()
            logger.info("Kafka consumer closed")


if __name__ == "__main__":
    # Can be run standalone: python -m app.kafka.ai_completion_consumer
    import os
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    run_ai_completion_consumer(bootstrap_servers)

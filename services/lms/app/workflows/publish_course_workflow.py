"""Temporal workflow for course publishing with rollback on failure."""

from datetime import timedelta
from typing import Dict, Any
from uuid import UUID

from temporalio import workflow, activity
from temporalio.exceptions import ApplicationError

from app.core.logging import get_logger

logger = get_logger(__name__)


# Activity functions (not class methods to avoid threading issues)
@activity.defn
async def mark_course_processing(course_id: str) -> Dict[str, Any]:
        """Mark course as published and processing - First step of workflow."""
        from app.db.session import SessionLocal
        # Import all models together to resolve SQLAlchemy relationships
        from app.modules.auth.models import User, Role, UserRole
        from app.modules.enrollments.models import Enrollment
        from app.modules.courses.models import Course, CourseStatus, CourseProcessingStatus
        
        db = SessionLocal()
        try:
            course = db.query(Course).filter(Course.id == UUID(course_id)).first()
            if not course:
                raise ApplicationError(f"Course not found: {course_id}")
            
            # Mark as PUBLISHED and PROCESSING
            course.status = CourseStatus.published
            course.processing_status = CourseProcessingStatus.processing
            db.commit()
            
            logger.info(f"Course marked as published and processing, course_id={course_id}")
            return {"course_id": course_id, "status": "published", "processing_status": "processing"}
        finally:
            db.close()

@activity.defn
async def publish_to_kafka(course_id: str, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """Publish course.published event to Kafka."""
        from app.integrations.kafka.producer import publish_json
        from app.models.outbox_event import OutboxEvent, OutboxStatus
        from app.db.session import SessionLocal
        from datetime import datetime
        
        db = SessionLocal()
        try:
            # Create and publish outbox event
            outbox = OutboxEvent(
                event_type="course.published",
                aggregate_type="course",
                aggregate_id=UUID(course_id),
                payload={
                    "course_id": course_id,
                    "course_data": course_data,
                    "published_at": datetime.utcnow().isoformat()
                },
                status=OutboxStatus.pending,
                attempts=0
            )
            
            db.add(outbox)
            db.commit()
            
            # Publish to Kafka
            publish_json(
                topic="course.events",
                key=course_id,
                value={
                    "event_id": str(outbox.id),
                    "event_type": "course.published",
                    "aggregate_id": course_id,
                    "payload": outbox.payload,
                    "created_at": outbox.created_at.isoformat()
                }
            )
            
            # Mark as published
            outbox.status = OutboxStatus.published
            db.commit()
            
            logger.info(f"Event published to Kafka, course_id={course_id}, outbox_id={outbox.id}")
            return {"course_id": course_id, "event_published": True}
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {str(e)}", exc_info=True)
            raise ApplicationError(f"Kafka publish failed: {str(e)}")
        finally:
            db.close()
    
@activity.defn
async def wait_for_ai_processing(course_id: str, timeout_seconds: int = 60) -> Dict[str, Any]:
        """Wait for AI service to publish course.processing_completed event via Kafka."""
        import asyncio
        import json
        import os
        from kafka import KafkaConsumer
        from kafka.errors import KafkaError
        
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        consumer = None
        try:
            # Create Kafka consumer to listen for AI processing completion events
            consumer = KafkaConsumer(
                "course.events",  # Listen to course events topic
                bootstrap_servers=[bootstrap_servers],
                group_id="lms-publishing-workflow",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: m,
                consumer_timeout_ms=int(timeout_seconds * 1000),  # timeout in milliseconds
            )
            
            logger.info(f"Waiting for course.processing_completed event for course_id={course_id}")
            start_time = asyncio.get_event_loop().time()
            
            for message in consumer:
                try:
                    # Decode message
                    payload = json.loads(message.value.decode("utf-8"))
                    event_type = payload.get("event_type")
                    aggregate_id = payload.get("aggregate_id")
                    
                    # Check if this is the completion event for our course
                    if event_type == "course.processing_completed" and aggregate_id == course_id:
                        logger.info(f"✅ AI processing completed for course_id={course_id}")
                        
                        processing_payload = payload.get("payload", {})
                        return {
                            "course_id": course_id,
                            "status": processing_payload.get("status", "completed"),
                            "chunks_created": processing_payload.get("total_chunks_created", 0),
                            "processed_assets": processing_payload.get("processed_assets", 0),
                        }
                    
                    # Check for failure event
                    elif event_type == "course.processing_failed" and aggregate_id == course_id:
                        error_msg = payload.get("payload", {}).get("error_message", "Unknown error")
                        logger.error(f"❌ AI processing failed for course_id={course_id}: {error_msg}")
                        raise ApplicationError(f"AI processing failed: {error_msg}")
                    
                except json.JSONDecodeError:
                    logger.warning("Failed to decode Kafka message as JSON")
                    continue
                
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout_seconds:
                    raise ApplicationError(
                        f"Timeout waiting for AI processing completion (>{timeout_seconds}s) for course {course_id}"
                    )
            
            # If we exit the loop without finding event, it means timeout occurred
            raise ApplicationError(
                f"AI processing timeout (>{timeout_seconds}s) for course {course_id}"
            )
            
        except KafkaError as e:
            logger.error(f"Kafka consumer error: {str(e)}")
            raise ApplicationError(f"Kafka error while waiting for AI processing: {str(e)}")
        finally:
            if consumer:
                consumer.close()
                logger.info("Kafka consumer closed")

@activity.defn
async def mark_course_ready(course_id: str) -> Dict[str, Any]:
        """Mark course as ready."""
        from app.db.session import SessionLocal
        # Import all models together to resolve SQLAlchemy relationships
        from app.modules.auth.models import User, Role, UserRole
        from app.modules.enrollments.models import Enrollment
        from app.modules.courses.models import Course, CourseProcessingStatus
        from datetime import datetime
        
        db = SessionLocal()
        try:
            course = db.query(Course).filter(Course.id == UUID(course_id)).first()
            if not course:
                raise ApplicationError(f"Course not found: {course_id}")
            
            course.processing_status = CourseProcessingStatus.ready
            course.processed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Course marked as READY, course_id={course_id}")
            return {"course_id": course_id, "status": "ready"}
        finally:
            db.close()

@activity.defn
async def rollback_course_publish(course_id: str) -> Dict[str, Any]:
        """Compensating activity: rollback course to DRAFT on failure."""
        from app.db.session import SessionLocal
        # Import all models together to resolve SQLAlchemy relationships
        from app.modules.auth.models import User, Role, UserRole
        from app.modules.enrollments.models import Enrollment
        from app.modules.courses.models import Course, CourseStatus, CourseProcessingStatus
        
        db = SessionLocal()
        try:
            course = db.query(Course).filter(Course.id == UUID(course_id)).first()
            if not course:
                logger.warning(f"Course not found during rollback: {course_id}")
                return {"course_id": course_id, "rollback": "not_found"}
            
            # Rollback to DRAFT
            course.status = CourseStatus.draft
            course.processing_status = CourseProcessingStatus.not_started
            course.processing_error = "Publishing failed and was rolled back"
            db.commit()
            
            logger.warning(f"Course publication rolled back to DRAFT, course_id={course_id}")
            return {"course_id": course_id, "rollback": "success"}
        except Exception as e:
            logger.error(f"Failed to rollback course: {str(e)}", exc_info=True)
            return {"course_id": course_id, "rollback": "failed", "error": str(e)}
        finally:
            db.close()


@workflow.defn
class PublishCourseWorkflow:
    """
    Workflow for publishing a course with automatic rollback on failure.
    
    Steps:
    1. Mark course as processing
    2. Publish course.published event to Kafka
    3. Wait for AI service to complete processing
    4. Mark course as ready
    
    If any step fails, rollback course to DRAFT status.
    """
    
    @workflow.run
    async def run(self, course_id: str, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow."""
        workflow.logger.info(f"Starting publish_course_workflow for course_id={course_id}")
        
        try:
            # Step 1: Mark as processing
            result1 = await workflow.execute_activity(
                mark_course_processing,
                args=[course_id],
                start_to_close_timeout=timedelta(seconds=10)
            )
            workflow.logger.info(f"Step 1 complete: {result1}")
            
            # Step 2: Publish to Kafka
            result2 = await workflow.execute_activity(
                publish_to_kafka,
                args=[course_id, course_data],
                start_to_close_timeout=timedelta(seconds=30)
            )
            workflow.logger.info(f"Step 2 complete: {result2}")
            
            # Step 3: Wait for AI processing (with 60s timeout)
            result3 = await workflow.execute_activity(
                wait_for_ai_processing,
                args=[course_id, 60],
                start_to_close_timeout=timedelta(seconds=90)  # activity timeout must be > poll timeout
            )
            workflow.logger.info(f"Step 3 complete: {result3}")
            
            # Step 4: Mark as ready
            result4 = await workflow.execute_activity(
                mark_course_ready,
                args=[course_id],
                start_to_close_timeout=timedelta(seconds=10)
            )
            workflow.logger.info(f"Step 4 complete: {result4}")
            
            return {
                "course_id": course_id,
                "status": "published",
                "workflow_status": "success",
                "chunks_created": result3.get("chunks_created", 0)
            }
            
        except Exception as e:
            workflow.logger.error(f"Workflow failed: {str(e)}, attempting rollback")
            
            # Execute compensating activity
            try:
                rollback_result = await workflow.execute_activity(
                    rollback_course_publish,
                    args=[course_id],
                    start_to_close_timeout=timedelta(seconds=10)
                )
                workflow.logger.info(f"Rollback complete: {rollback_result}")
            except Exception as rollback_error:
                workflow.logger.error(f"Rollback failed: {str(rollback_error)}")
            
            raise ApplicationError(f"Course publishing failed: {str(e)}")


# Keep function wrapper for backward compatibility
async def publish_course_workflow(course_id: str, course_data: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper function for starting the workflow."""
    return await PublishCourseWorkflow().run(course_id, course_data)

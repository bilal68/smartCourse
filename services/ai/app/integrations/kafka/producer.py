"""Kafka producer for publishing events."""
import json
from typing import Any, Dict
from uuid import uuid4

from confluent_kafka import Producer

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global producer instance
_producer: Producer = None


def get_producer() -> Producer:
    """Get or create Kafka producer."""
    global _producer
    if _producer is None:
        config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS
        }
        _producer = Producer(config)
    return _producer


def publish_course_completion(
    course_id: str,
    total_chunks_created: int,
    total_embeddings_created: int,
    processed_assets: int
) -> None:
    """
    Publish course.processing_completed event.
    
    This signals LMS that AI processing is done successfully.
    """
    event = {
        "event_id": str(uuid4()),
        "event_type": "course.processing_completed",
        "aggregate_type": "course",
        "aggregate_id": course_id,
        "payload": {
            "course_id": course_id,
            "total_chunks_created": total_chunks_created,
            "total_embeddings_created": total_embeddings_created,
            "processed_assets": processed_assets,
            "status": "completed"
        }
    }
    
    producer = get_producer()
    try:
        producer.produce(
            topic=settings.KAFKA_COURSE_TOPIC,
            key=course_id,
            value=json.dumps(event),
            callback=lambda err, msg: logger.error(f"Failed to deliver message: {err}") if err else None
        )
        producer.flush()  # Ensure message is sent
        logger.info(f"Published course.processing_completed for course {course_id}")
    except Exception as e:
        logger.error(f"Failed to publish course completion: {str(e)}")


def publish_course_failure(course_id: str, error_message: str) -> None:
    """
    Publish course.processing_failed event.
    
    This signals LMS that AI processing failed.
    """
    event = {
        "event_id": str(uuid4()),
        "event_type": "course.processing_failed",
        "aggregate_type": "course",
        "aggregate_id": course_id,
        "payload": {
            "course_id": course_id,
            "error_message": error_message,
            "status": "failed"
        }
    }
    
    producer = get_producer()
    try:
        producer.produce(
            topic=settings.KAFKA_COURSE_TOPIC,
            key=course_id,
            value=json.dumps(event),
            callback=lambda err, msg: logger.error(f"Failed to deliver message: {err}") if err else None
        )
        producer.flush()
        logger.error(f"Published course.processing_failed for course {course_id}: {error_message}")
    except Exception as e:
        logger.error(f"Failed to publish course failure: {str(e)}")

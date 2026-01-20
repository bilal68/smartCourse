"""Kafka producer for publishing events."""
import json
from typing import Any, Dict
from uuid import uuid4

from kafka import KafkaProducer

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global producer instance
_producer: KafkaProducer = None


def get_producer() -> KafkaProducer:
    """Get or create Kafka producer."""
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
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
    future = producer.send(settings.KAFKA_COURSE_TOPIC, key=course_id.encode(), value=event)
    future.get(timeout=10)  # Block until sent
    
    logger.info(f"Published course.processing_completed for course {course_id}")


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
    future = producer.send(settings.KAFKA_COURSE_TOPIC, key=course_id.encode(), value=event)
    future.get(timeout=10)
    
    logger.error(f"Published course.processing_failed for course {course_id}: {error_message}")

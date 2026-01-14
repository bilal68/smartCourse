"""Kafka consumer and producer for AI service."""

import json
import asyncio
from typing import Dict, Any, Callable
import uuid

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIKafkaProducer:
    """Kafka producer for AI service."""
    
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        logger.info("AI Kafka producer initialized")
    
    def publish_content_processed(self, course_id: str, processing_result: Dict[str, Any]):
        """Publish content processing completed event."""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "course.processing_completed",  # Match what LMS workflow expects
            "aggregate_id": course_id,  # Match LMS event structure
            "payload": processing_result,
            "service": "ai-service",
            "timestamp": str(uuid.uuid1().time)
        }
        
        try:
            self.producer.send('course.events', event)
            self.producer.flush()
            logger.info(f"Published course processing completed event, course_id={course_id}")
        except KafkaError as e:
            logger.error(f"Failed to publish course processing completed event, course_id={course_id}, error={str(e)}")
    
    def close(self):
        """Close the producer."""
        self.producer.close()


class AIKafkaConsumer:
    """Kafka consumer for AI service."""
    
    def __init__(self):
        self.consumer = KafkaConsumer(
            'course.events',
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',  # Process all messages from beginning
            enable_auto_commit=True
        )
        self.handlers: Dict[str, Callable] = {}
        logger.info("AI Kafka consumer initialized")
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler."""
        self.handlers[event_type] = handler
        logger.info(f"🎯 Registered event handler: event_type={event_type}, handler={handler.__name__}")
        logger.info(f"📝 Total handlers registered: {list(self.handlers.keys())}")
    
    def start_consuming(self):
        """Start consuming messages."""
        logger.info("Starting Kafka consumer for AI service")
        try:
            for message in self.consumer:
                try:
                    event = message.value
                    event_type = event.get('event_type')
                    
                    # Handle course.published events (our main interest)
                    if event_type == 'course.published':
                        logger.info(f"📨 Processing course.published: course_id={event.get('aggregate_id')}")
                        if event_type in self.handlers:
                            handler = self.handlers[event_type]
                            handler(event)
                        else:
                            logger.error(f"❌ No handler for course.published - this should not happen!")
                    
                    # Silently skip content.processed events (our own responses)
                    elif event_type == 'content.processed':
                        # These are responses from AI service - LMS should handle them
                        continue
                    
                    # Log unknown event types for debugging
                    else:
                        logger.warning(f"🔍 Unknown event type: {event_type}, event_id={event.get('event_id')}")
                        
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error("Consumer error", error=str(e), exc_info=True)
        finally:
            self.consumer.close()
            logger.info("Kafka consumer closed")
    
    def close(self):
        """Close the consumer."""
        self.consumer.close()


# Global instances
_producer = None
_consumer = None


def get_kafka_producer() -> AIKafkaProducer:
    """Get the global Kafka producer instance."""
    global _producer
    if _producer is None:
        _producer = AIKafkaProducer()
    return _producer


def get_kafka_consumer() -> AIKafkaConsumer:
    """Get the global Kafka consumer instance."""
    global _consumer
    if _consumer is None:
        _consumer = AIKafkaConsumer()
    return _consumer
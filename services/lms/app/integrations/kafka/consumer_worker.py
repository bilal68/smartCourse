"""Kafka consumer worker for LMS service using kafka-python."""

import json
import logging
import os
import sys
import time
from typing import Any, Optional

try:
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
    _HAS_KAFKA = True
except ModuleNotFoundError:
    KafkaConsumer = None
    KafkaError = Exception
    _HAS_KAFKA = False

from app.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)

# Config
TOPIC = os.getenv("KAFKA_TOPIC", "course.events")
TASK_NAME = os.getenv(
    "KAFKA_TASK_NAME",
    "tasks.notification_tasks.notify_course_published",
)

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "lms-service-group")

POLL_TIMEOUT = float(os.getenv("KAFKA_POLL_TIMEOUT", "1.0"))
IDLE_LOG_EVERY = float(os.getenv("KAFKA_IDLE_LOG_EVERY", "10"))
EXIT_AFTER_SECONDS = float(os.getenv("KAFKA_EXIT_AFTER_SECONDS", "0"))


def _safe_decode_json(msg) -> Optional[dict[str, Any]]:
    """Decode Kafka message -> JSON dict. Returns None on errors."""
    try:
        if msg.value is None:
            return None
        text = msg.value.decode("utf-8")
        return json.loads(text)
    except Exception:
        logger.exception("Failed to decode/parse message as JSON")
        return None


def start_consumer() -> None:
    """Start the Kafka consumer worker."""
    if not _HAS_KAFKA:
        logger.error(
            "kafka-python package is not installed. Install with: pip install kafka-python"
        )
        sys.exit(1)
    
    logger.info("✅ Starting Kafka consumer")
    logger.info(
        f"Bootstrap={BOOTSTRAP} | Group={GROUP_ID} | Topic={TOPIC} | Task={TASK_NAME}"
    )

    # Create consumer with kafka-python
    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=[BOOTSTRAP],
            group_id=GROUP_ID,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            consumer_timeout_ms=int(POLL_TIMEOUT * 1000),
            value_deserializer=lambda m: m  # We'll decode manually
        )
    except Exception as e:
        logger.error(f"Failed to create Kafka consumer: {e}")
        logger.info("Make sure Kafka server is running on localhost:9092")
        sys.exit(1)

    last_idle_log = time.monotonic()
    started_at = time.monotonic()

    try:
        logger.info("✅ Subscribed. Waiting for messages...")

        for message in consumer:
            if (
                EXIT_AFTER_SECONDS > 0
                and (time.monotonic() - started_at) > EXIT_AFTER_SECONDS
            ):
                logger.info(f"⏹ Exiting because KAFKA_EXIT_AFTER_SECONDS={EXIT_AFTER_SECONDS}")
                break

            payload = _safe_decode_json(message)
            if not payload:
                continue

            logger.info(
                f"📨 Received message: topic={message.topic}, partition={message.partition}, "
                f"offset={message.offset}, key={message.key.decode('utf-8') if message.key else None}, "
                f"event_type={payload.get('event_type')}"
            )

            try:
                # Handle different event types
                event_type = payload.get("event_type")
                
                if event_type == "content.processed":
                    # Handle content processing completion from AI service
                    from app.integrations.kafka.handlers import get_lms_event_handler
                    handler = get_lms_event_handler()
                    handler.handle_content_processed(payload)
                    logger.info("✅ Handled content.processed event")
                else:
                    # For other events, use original Celery task dispatch
                    celery_app.send_task(TASK_NAME, args=[payload])
                    logger.info(f"✅ Dispatched to Celery task={TASK_NAME}")
                    
            except Exception as e:
                logger.exception(f"Failed to handle event: event_type={payload.get('event_type')}")
                continue

    except KeyboardInterrupt:
        logger.info("❌ Interrupted by user")
    except Exception as e:
        logger.error(f"Consumer error: {str(e)}", exc_info=True)
    finally:
        if 'consumer' in locals():
            consumer.close()
            logger.info("🔒 Kafka consumer closed")


if __name__ == "__main__":
    start_consumer()

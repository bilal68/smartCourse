import json
import logging
import os
import sys
import time
from typing import Any, Optional

try:
    from confluent_kafka import Consumer, KafkaException, Message
    _HAS_CONFLUENT = True
except ModuleNotFoundError:
    Consumer = None
    KafkaException = Exception
    Message = None
    _HAS_CONFLUENT = False

from app.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)

# Config
TOPIC = os.getenv("KAFKA_TOPIC", "smartcourse.course-events")
TASK_NAME = os.getenv(
    "KAFKA_TASK_NAME",
    "tasks.notification_tasks.notify_course_published",
)

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "smartcourse-notifications")

conf = {
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP_ID,
    "auto.offset.reset": os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
    "enable.auto.commit": False,
}

POLL_TIMEOUT = float(os.getenv("KAFKA_POLL_TIMEOUT", "1.0"))
IDLE_LOG_EVERY = float(os.getenv("KAFKA_IDLE_LOG_EVERY", "10"))
EXIT_AFTER_SECONDS = float(os.getenv("KAFKA_EXIT_AFTER_SECONDS", "0"))


def _safe_decode_json(msg) -> Optional[dict[str, Any]]:
    """Decode Kafka message -> JSON dict. Returns None on errors."""
    try:
        raw = msg.value()
        if raw is None:
            return None
        text = raw.decode("utf-8")
        return json.loads(text)
    except Exception:
        logger.exception("Failed to decode/parse message as JSON")
        return None


def start_consumer() -> None:
    """Start the Kafka consumer worker."""
    if not _HAS_CONFLUENT:
        logger.error(
            "confluent_kafka package is not installed. Install with: pip install confluent-kafka"
        )
        sys.exit(1)
    
    logger.info("✅ Starting Kafka consumer")
    logger.info(
        "Bootstrap=%s | Group=%s | Topic=%s | Task=%s",
        BOOTSTRAP,
        GROUP_ID,
        TOPIC,
        TASK_NAME,
    )

    c = Consumer(conf)
    c.subscribe([TOPIC])

    last_idle_log = time.monotonic()
    started_at = time.monotonic()

    try:
        logger.info("✅ Subscribed. Waiting for messages...")

        while True:
            if (
                EXIT_AFTER_SECONDS > 0
                and (time.monotonic() - started_at) > EXIT_AFTER_SECONDS
            ):
                logger.info(
                    "⏹ Exiting because KAFKA_EXIT_AFTER_SECONDS=%s", EXIT_AFTER_SECONDS
                )
                break

            msg = c.poll(POLL_TIMEOUT)

            if msg is None:
                now = time.monotonic()
                if (now - last_idle_log) > IDLE_LOG_EVERY:
                    logger.info("⏸ No messages (still polling...)")
                    last_idle_log = now
                continue

            if msg.error():
                if msg.error().code() == KafkaException._PARTITION_EOF:
                    continue
                else:
                    logger.error("Kafka error: %s", msg.error())
                    continue

            payload = _safe_decode_json(msg)
            if not payload:
                c.commit(msg)
                continue

            logger.info(
                "📨 Received message",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                key=msg.key().decode("utf-8") if msg.key() else None,
            )

            try:
                celery_app.send_task(TASK_NAME, args=[payload])
                logger.info("✅ Dispatched to Celery task=%s", TASK_NAME)
            except Exception as e:
                logger.exception("Failed to dispatch task")
                continue

            c.commit(msg)

    except KeyboardInterrupt:
        logger.info("❌ Interrupted by user")
    finally:
        logger.info("🔒 Closing consumer")
        c.close()


if __name__ == "__main__":
    start_consumer()

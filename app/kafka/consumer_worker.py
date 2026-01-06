import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

try:
    from confluent_kafka import Consumer, KafkaException, Message
    _HAS_CONFLUENT = True
except ModuleNotFoundError:  # pragma: no cover - helpful fallback when running standalone
    Consumer = None
    KafkaException = Exception
    Message = None
    _HAS_CONFLUENT = False
from app.celery_app import celery_app  # your existing celery app

# -------------------------
# Logging (use structlog configured by app.core.logging)
# -------------------------
from app.core.logging import get_logger

logger = get_logger(__name__)

# -------------------------
# Config
# -------------------------
TOPIC = os.getenv("KAFKA_TOPIC", "smartcourse.course-events")
TASK_NAME = os.getenv(
    "KAFKA_TASK_NAME",
    "tasks.notification_tasks.notify_course_published",  # change if your celery task name differs
)

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "smartcourse-notifications")

# Consumer config (Confluent)
conf = {
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP_ID,
    "auto.offset.reset": os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
    "enable.auto.commit": False,
}

POLL_TIMEOUT = float(os.getenv("KAFKA_POLL_TIMEOUT", "1.0"))
IDLE_LOG_EVERY = float(os.getenv("KAFKA_IDLE_LOG_EVERY", "10"))  # seconds
EXIT_AFTER_SECONDS = float(os.getenv("KAFKA_EXIT_AFTER_SECONDS", "0"))  # 0 => never


def _safe_decode_json(msg: Message) -> Optional[Dict[str, Any]]:
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


def run() -> None:
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
            # Optional: auto-exit in dev if you want
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
                # heartbeat log so you know it's alive
                now = time.monotonic()
                if now - last_idle_log >= IDLE_LOG_EVERY:
                    logger.debug("⏳ Idle... no messages yet")
                    last_idle_log = now
                continue

            if msg.error():
                # Kafka-level error
                logger.error("Kafka message error: %s", msg.error())
                continue

            # Breakpoint-friendly line (set breakpoint here)
            payload = _safe_decode_json(msg)
            if not payload:
                # Decide if you want to commit bad messages or not.
                # If you commit here, you won't re-read the bad one.
                logger.warning(
                    "Skipping message (empty/invalid JSON). Committing offset to avoid reprocessing."
                )
                try:
                    c.commit(msg)
                except Exception:
                    logger.exception("Commit failed after invalid message")
                continue

            event = payload.get("event")
            logger.info("📩 Received event=%s", event)

            try:
                if event == "course.published":
                    result = celery_app.send_task(TASK_NAME, args=[payload])
                    logger.info(
                        "🚀 Celery task queued: %s (id=%s)",
                        TASK_NAME,
                        getattr(result, "id", None),
                    )

                # Commit after enqueue / processing
                c.commit(msg)
                logger.debug("✅ Offset committed")

            except Exception:
                logger.exception(
                    "Error handling message (event=%s). NOT committing offset.", event
                )
                # Not committing means it can be retried (depending on your consumer behavior)

    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user (Ctrl+C)")
    except KafkaException:
        logger.exception("Kafka exception occurred")
    finally:
        logger.info("Closing consumer...")
        c.close()
        logger.info("✅ Consumer closed")


if __name__ == "__main__":
    # Make stdout unbuffered (helps with seeing logs immediately in some terminals)
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    run()

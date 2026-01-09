from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.integrations.kafka.producer import publish_json
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

TOPIC_MAP = {
    "course.published": "smartcourse.course-events",
    "enrollment.created": "smartcourse.enrollment-events",
    # "asset.progress.updated": "smartcourse.progress-events",  # if you add later
}

MAX_ATTEMPTS = 5


@celery_app.task(
    name="app.tasks.outbox_tasks.publish_pending_outbox",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def publish_pending_outbox(self, batch_size: int = 50) -> dict:
    db: Session = SessionLocal()
    try:
        valid_types = list(TOPIC_MAP.keys())
        if not valid_types:
            logger.info("publish_pending_outbox: TOPIC_MAP empty")
            return {"published": 0, "failed": 0, "checked": 0}

        # Handle nullable attempts: coalesce(attempts, 0) < MAX_ATTEMPTS
        events = (
            db.query(OutboxEvent)
            .filter(
                OutboxEvent.status == OutboxStatus.pending,
                OutboxEvent.event_type.in_(valid_types),
                func.coalesce(OutboxEvent.attempts, 0) < MAX_ATTEMPTS,
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(batch_size)
            .all()
        )

        published = 0
        failed = 0

        logger.info("publish_pending_outbox: found %d pending events", len(events))

        for evt in events:
            topic = TOPIC_MAP[evt.event_type]  # safe because filtered

            try:
                publish_json(
                    topic=topic,
                    key=str(evt.aggregate_id),
                    value={
                        "event_id": str(evt.id),
                        "event_type": evt.event_type,
                        "aggregate_type": evt.aggregate_type,
                        "aggregate_id": str(evt.aggregate_id),
                        "payload": evt.payload,
                        "created_at": (
                            evt.created_at.isoformat() if evt.created_at else None
                        ),
                    },
                )

                evt.status = OutboxStatus.published
                evt.last_error = None
                evt.attempts = (evt.attempts or 0) + 1
                db.commit()
                published += 1

            except Exception as e:
                evt.attempts = (evt.attempts or 0) + 1
                evt.last_error = str(e)

                # retry until MAX_ATTEMPTS, then dead-letter as failed
                if evt.attempts >= MAX_ATTEMPTS:
                    evt.status = OutboxStatus.failed
                    failed += 1
                else:
                    evt.status = OutboxStatus.pending

                db.commit()

        return {"published": published, "failed": failed, "checked": len(events)}
    finally:
        db.close()

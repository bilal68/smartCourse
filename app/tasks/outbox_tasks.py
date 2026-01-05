from __future__ import annotations

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.kafka.producer import publish_json
from app.models.outbox_event import OutboxEvent, OutboxStatus

TOPIC_MAP = {
    "course.published": "smartcourse.course-events",
    "enrollment.created": "smartcourse.enrollment-events",
    # later:
    # "course.updated": "smartcourse.course-events",
}


@celery_app.task(
    name="app.tasks.outbox_tasks.publish_pending_outbox",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def publish_pending_outbox(self, batch_size: int = 50) -> dict:
    """
    Pull pending outbox rows from Postgres and publish them to Kafka.
    Marks rows as published/failed so we can retry safely.
    """
    db: Session = SessionLocal()
    try:
        events = (
            db.query(OutboxEvent)
            .filter(OutboxEvent.status == OutboxStatus.pending)
            .order_by(OutboxEvent.created_at.asc())
            .limit(batch_size)
            .all()
        )

        published = 0
        failed = 0

        for evt in events:
            topic = TOPIC_MAP.get(evt.event_type)

            if not topic:
                evt.status = OutboxStatus.failed
                evt.last_error = f"Unknown event_type: {evt.event_type}"
                evt.attempts = (evt.attempts or 0) + 1
                failed += 1
                continue

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
                published += 1
            except Exception as e:
                evt.status = OutboxStatus.failed
                evt.last_error = str(e)
                failed += 1
            finally:
                evt.attempts = (evt.attempts or 0) + 1

        db.commit()
        return {"published": published, "failed": failed, "checked": len(events)}
    finally:
        db.close()

from __future__ import annotations

import json
import os

from confluent_kafka import Producer

from app.core.logging import get_logger

logger = get_logger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

producer_config = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "client.id": "smartcourse-lms-producer",
}

_producer = Producer(producer_config)


def delivery_report(err, msg):
    if err is not None:
        logger.error("message delivery failed", error=str(err))
    else:
        logger.debug(
            "message delivered",
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
        )


def publish_json(topic: str, key: str, value: dict):
    """
    Publish a JSON message to a Kafka topic.
    key: string used for partitioning
    value: dict that will be serialized to JSON
    """
    try:
        _producer.produce(
            topic=topic,
            key=key.encode("utf-8") if key else None,
            value=json.dumps(value).encode("utf-8"),
            callback=delivery_report,
        )
        _producer.poll(0)  # trigger callbacks for any completed messages
    except Exception as e:
        logger.error("failed to publish to kafka", topic=topic, error=str(e))
        raise


def flush_producer():
    """Flush any buffered messages."""
    _producer.flush()

from __future__ import annotations

import json
import os
from typing import Any

from confluent_kafka import Producer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

_producer: Producer | None = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({"bootstrap.servers": BOOTSTRAP})
    return _producer


def publish_json(topic: str, key: str, value: dict[str, Any]) -> None:
    """
    Publish a JSON message and block until it's delivered (simple + reliable for assignments).
    """
    p = get_producer()
    payload = json.dumps(value).encode("utf-8")

    delivery_error: list[Exception] = []

    def delivery_cb(err, msg):
        if err is not None:
            delivery_error.append(RuntimeError(str(err)))

    p.produce(topic=topic, key=key.encode("utf-8"), value=payload, callback=delivery_cb)
    p.flush(10)

    if delivery_error:
        raise delivery_error[0]

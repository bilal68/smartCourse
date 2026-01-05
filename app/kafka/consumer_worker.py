from __future__ import annotations

import json
import os
import time

from confluent_kafka import Consumer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "smartcourse-consumers")

TOPICS = [
    "smartcourse.course-events",
    "smartcourse.enrollment-events",
]


def main():
    c = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    c.subscribe(TOPICS)

    print(f"[consumer] bootstrap={BOOTSTRAP} group={GROUP_ID} topics={TOPICS}")

    try:
        while True:
            msg = c.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print("[consumer] error:", msg.error())
                continue

            key = msg.key().decode("utf-8") if msg.key() else None
            value = json.loads(msg.value().decode("utf-8"))

            print(f"[consumer] topic={msg.topic()} key={key} value={value}")

            # later: call handlers based on value["event_type"]
            # and write processed_events for idempotency.

            c.commit(message=msg, asynchronous=False)
    finally:
        c.close()


if __name__ == "__main__":
    main()

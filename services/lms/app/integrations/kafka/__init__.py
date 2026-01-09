# app/integrations/kafka/__init__.py
"""
Kafka integration module for event publishing and consuming.
"""

from app.integrations.kafka.producer import publish_json
from app.integrations.kafka.consumer_worker import start_consumer

__all__ = ["publish_json", "start_consumer"]

# app/integrations/kafka/__init__.py
"""
Kafka integration module for event publishing and consuming.
"""

from app.integrations.kafka.producer import publish_json
from app.integrations.kafka.ai_completion_consumer import run_ai_completion_consumer

__all__ = ["publish_json", "run_ai_completion_consumer"]

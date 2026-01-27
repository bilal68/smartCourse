# app/models/__init__.py
# Only shared models that are not part of domain modules
# Note: ContentChunk removed - now managed by AI service

from .certificate import Certificate
from .outbox_event import OutboxEvent

__all__ = [
    "Certificate",
    "OutboxEvent",
]

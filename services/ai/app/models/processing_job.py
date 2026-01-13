"""Processing job model for tracking AI content processing."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ProcessingStatus(str, Enum):
    """Status of content processing job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJob(Base):
    """Model for tracking content processing jobs."""
    
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Processing details
    status = Column(String, nullable=False, default=ProcessingStatus.PENDING)
    total_assets = Column(Integer, default=0)
    processed_assets = Column(Integer, default=0)
    failed_assets = Column(Integer, default=0)
    total_chunks_created = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    failed_asset_details = Column(JSON, default=list)  # List of failed assets with errors
    
    # Processing metadata
    processing_metadata = Column(JSON, default=dict)  # Additional processing info
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of processing."""
        if self.total_assets == 0:
            return 0.0
        return (self.processed_assets / self.total_assets) * 100
    
    @property
    def is_completed(self) -> bool:
        """Check if processing is completed (success or failure)."""
        return self.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, course_id={self.course_id}, status={self.status})>"
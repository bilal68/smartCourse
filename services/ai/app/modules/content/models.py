"""Content module models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY, REAL
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class ProcessingStatus(str, Enum):
    """Status of content processing job."""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"


class ContentChunk(Base):
    """Model for storing processed content chunks."""
    
    __tablename__ = "content_chunks"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    asset_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    
    # Content data
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    char_count = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)  # Add token count for stats
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    embedding = relationship("ChunkEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ContentChunk(id={self.id}, course_id={self.course_id}, chunk_index={self.chunk_index})>"


class ChunkEmbedding(Base):
    """
    Stores vector embeddings for content chunks.
    One embedding per chunk for semantic search/RAG.
    """
    __tablename__ = "chunk_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("content_chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    
    # Vector embedding - flexible dimension based on model
    embedding: Mapped[Vector] = mapped_column(Vector(), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    # Relationships
    chunk: Mapped["ContentChunk"] = relationship("ContentChunk", back_populates="embedding")

    __table_args__ = (
        Index('ix_chunk_embeddings_course_id', 'course_id'),
        Index('ix_chunk_embeddings_model_name', 'model_name'),
    )


class ProcessingJob(Base):
    """Model for tracking content processing jobs."""
    
    __tablename__ = "processing_jobs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(PG_UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Processing details
    status = Column(String, nullable=False, default=ProcessingStatus.PENDING)
    total_assets = Column(Integer, default=0)
    processed_assets = Column(Integer, default=0)
    failed_assets = Column(Integer, default=0)
    total_chunks_created = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    failed_asset_details = Column(JSON, default=list)
    
    # Processing metadata
    processing_metadata = Column(JSON, default=dict)
    
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
        return (self.processed_assets - self.failed_assets) / self.total_assets
    
    @property
    def is_completed(self) -> bool:
        """Check if processing is completed."""
        return self.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, course_id={self.course_id}, status={self.status})>"


class CourseAnalysis(Base):
    """Model for storing AI-generated course analysis."""
    
    __tablename__ = "course_analysis"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(PG_UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Analysis content
    summary = Column(Text, nullable=True)
    key_topics = Column(JSON, default=list)  # List of strings
    difficulty_score = Column(REAL, nullable=True)  # 0.0 - 1.0
    estimated_duration = Column(String(50), nullable=True)  # e.g., "2-3 hours"
    
    # Structured insights
    content_insights = Column(JSON, default=dict)
    learning_objectives = Column(JSON, default=list)
    prerequisites = Column(JSON, default=list)
    
    # Quality metrics
    content_quality_score = Column(REAL, nullable=True)  # 0.0 - 1.0
    engagement_score = Column(REAL, nullable=True)  # 0.0 - 1.0
    confidence_score = Column(REAL, nullable=True)  # AI confidence in analysis
    
    # Metadata
    analysis_version = Column(String(20), nullable=False, default="1.0")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<CourseAnalysis(id={self.id}, course_id={self.course_id}, version={self.analysis_version})>"
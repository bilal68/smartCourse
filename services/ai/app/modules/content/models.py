"""Content models for AI service - RAG and embeddings."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, REAL
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
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Content data
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    char_count = Column(Integer, nullable=True)
    # token_count = Column(Integer, nullable=True)  # TODO: Add via migration
    
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("content_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One embedding per chunk
        index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Vector embedding - match actual database column name
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    
    # Metadata for the embedding
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="multi-qa-MiniLM-L6-cos-v1")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    chunk = relationship("ContentChunk", back_populates="embedding")
    
    def __repr__(self):
        return f"<ChunkEmbedding(id={self.id}, chunk_id={self.chunk_id}, model={self.model_name})>"


class ProcessingJob(Base):
    """Track content processing jobs for courses."""
    __tablename__ = "processing_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Job details
    status: Mapped[ProcessingStatus] = mapped_column(String(20), nullable=False, default=ProcessingStatus.PENDING)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=True)  # Set when processing starts
    processed_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, course_id={self.course_id}, status={self.status})>"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate processing progress as percentage."""
        if not self.total_chunks or self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100


class CourseAnalysis(Base):
    """Store analysis results and metadata for processed courses."""
    __tablename__ = "course_analysis"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Analysis results
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    total_characters: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_chunk_size: Mapped[float] = mapped_column(REAL, nullable=False)
    
    # Content metadata extracted during processing
    course_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    course_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_topics: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Search optimization
    is_searchable: Mapped[bool] = mapped_column(nullable=False, default=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<CourseAnalysis(id={self.id}, course_id={self.course_id}, chunks={self.total_chunks})>"


# Create database indexes for better query performance
Index('idx_chunk_embeddings_vector', ChunkEmbedding.embedding, postgresql_using='ivfflat')
Index('idx_content_chunks_course_created', ContentChunk.course_id, ContentChunk.created_at)
Index('idx_processing_jobs_status', ProcessingJob.status, ProcessingJob.created_at)
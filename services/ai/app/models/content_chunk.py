"""Content chunk model for AI service database."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY, REAL

from app.db.base import Base


class ContentChunk(Base):
    """Model for storing processed content chunks."""
    
    __tablename__ = "content_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Made nullable to match DB
    
    # Content data
    content = Column(Text, nullable=False)  # Changed from chunk_text to content
    chunk_index = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=True)  # Added to match DB
    end_char = Column(Integer, nullable=True)    # Added to match DB
    char_count = Column(Integer, nullable=True)  # Added to match DB
    
    # Vector embeddings for semantic search - may need separate migration
    # embeddings = Column(ARRAY(REAL), nullable=True)  # Store as array of floats
    
    # Additional metadata - may need separate migration  
    # extra = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ContentChunk(id={self.id}, course_id={self.course_id}, asset_id={self.asset_id}, chunk_index={self.chunk_index})>"
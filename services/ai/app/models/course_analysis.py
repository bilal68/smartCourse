"""Course analysis model for storing AI-generated insights."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, DateTime, JSON, Float
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CourseAnalysis(Base):
    """Model for storing AI-generated course analysis and insights."""
    
    __tablename__ = "course_analysis"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Analysis results
    summary = Column(Text, nullable=True)  # AI-generated course summary
    key_topics = Column(JSON, default=list)  # List of main topics/themes
    difficulty_score = Column(Float, nullable=True)  # 0-10 difficulty rating
    estimated_duration = Column(String, nullable=True)  # e.g., "2 hours", "1 week"
    
    # Content insights
    content_insights = Column(JSON, default=dict)  # Various AI insights
    learning_objectives = Column(JSON, default=list)  # Extracted learning objectives
    prerequisites = Column(JSON, default=list)  # Recommended prerequisites
    
    # Quality metrics
    content_quality_score = Column(Float, nullable=True)  # 0-100 quality score
    engagement_score = Column(Float, nullable=True)  # 0-100 engagement prediction
    
    # Analysis metadata
    analysis_version = Column(String, default="1.0")  # Version of analysis algorithm
    confidence_score = Column(Float, nullable=True)  # Confidence in analysis
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<CourseAnalysis(id={self.id}, course_id={self.course_id}, difficulty={self.difficulty_score})>"
"""API schemas for AI service."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID

from app.models.processing_job import ProcessingStatus


class ContentChunkResponse(BaseModel):
    """Response model for content chunk."""
    id: UUID
    course_id: UUID
    asset_id: UUID
    chunk_index: int
    content: str  # Changed from chunk_text to content
    start_char: Optional[int] = None
    end_char: Optional[int] = None  
    char_count: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProcessingJobResponse(BaseModel):
    """Response model for processing job."""
    id: UUID
    course_id: UUID
    status: ProcessingStatus
    total_assets: int
    processed_assets: int
    failed_assets: int
    total_chunks_created: int
    error_message: Optional[str] = None
    failed_asset_details: List[Dict[str, Any]] = []
    success_rate: float
    is_completed: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CourseAnalysisResponse(BaseModel):
    """Response model for course analysis."""
    id: UUID
    course_id: UUID
    summary: Optional[str] = None
    key_topics: List[str] = []
    difficulty_score: Optional[float] = None
    estimated_duration: Optional[str] = None
    content_insights: Dict[str, Any] = {}
    learning_objectives: List[str] = []
    prerequisites: List[str] = []
    content_quality_score: Optional[float] = None
    engagement_score: Optional[float] = None
    analysis_version: str
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(..., min_length=1, max_length=500)
    course_ids: Optional[List[UUID]] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Individual search result."""
    chunk_id: UUID
    course_id: UUID
    asset_id: UUID
    content: str  # Changed from chunk_text to content
    similarity_score: float
    chunk_index: int


class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
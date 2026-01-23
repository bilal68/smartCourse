"""Content management routes."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.content.service import ContentService
from app.api.schemas import (
    ContentChunkResponse, 
    ProcessingJobResponse, 
    CourseAnalysisResponse
)

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/courses/{course_id}/chunks", response_model=List[ContentChunkResponse])
async def get_course_chunks(
    course_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get content chunks for a specific course."""
    content_service = ContentService(db)
    return content_service.get_course_chunks(course_id, limit, offset)


@router.get("/assets/{asset_id}/chunks", response_model=List[ContentChunkResponse])
async def get_asset_chunks(
    asset_id: UUID,
    db: Session = Depends(get_db)
):
    """Get content chunks for a specific asset."""
    content_service = ContentService(db)
    return content_service.get_asset_chunks(asset_id)


@router.get("/courses/{course_id}/processing-status", response_model=ProcessingJobResponse)
async def get_processing_status(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get processing status for a course."""
    content_service = ContentService(db)
    return content_service.get_processing_status(course_id)


@router.get("/processing-jobs", response_model=List[ProcessingJobResponse])
async def get_processing_jobs(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get list of processing jobs."""
    content_service = ContentService(db)
    return content_service.get_processing_jobs(status, limit, offset)


@router.get("/courses/{course_id}/analysis", response_model=CourseAnalysisResponse)
async def get_course_analysis(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get AI-generated analysis for a course."""
    content_service = ContentService(db)
    return content_service.get_course_analysis(course_id)


@router.post("/generate-embeddings")
async def generate_embeddings(
    course_id: Optional[UUID] = None,
    force_regenerate: bool = Query(default=True, description="Regenerate embeddings even if they exist"),
    db: Session = Depends(get_db)
):
    """Generate embeddings for content chunks using the configured provider."""
    content_service = ContentService(db)
    return content_service.generate_embeddings(course_id, force_regenerate)


@router.get("/courses/{course_id}/stats")
async def get_course_stats(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get statistics for a course's content."""
    content_service = ContentService(db)
    return content_service.get_course_stats(course_id)
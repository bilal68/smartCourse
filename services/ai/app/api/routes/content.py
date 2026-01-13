"""Content and processing API routes for AI service."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content_chunk import ContentChunk
from app.models.processing_job import ProcessingJob
from app.models.course_analysis import CourseAnalysis
from app.api.schemas import (
    ContentChunkResponse, 
    ProcessingJobResponse, 
    CourseAnalysisResponse,
    SearchRequest,
    SearchResponse
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
    chunks = (
        db.query(ContentChunk)
        .filter(ContentChunk.course_id == course_id)
        .order_by(ContentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return chunks


@router.get("/assets/{asset_id}/chunks", response_model=List[ContentChunkResponse])
async def get_asset_chunks(
    asset_id: UUID,
    db: Session = Depends(get_db)
):
    """Get content chunks for a specific asset."""
    chunks = (
        db.query(ContentChunk)
        .filter(ContentChunk.asset_id == asset_id)
        .order_by(ContentChunk.chunk_index)
        .all()
    )
    return chunks


@router.get("/courses/{course_id}/processing-status", response_model=ProcessingJobResponse)
async def get_processing_status(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get processing status for a course."""
    job = db.query(ProcessingJob).filter(ProcessingJob.course_id == course_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return job


@router.get("/processing-jobs", response_model=List[ProcessingJobResponse])
async def get_processing_jobs(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get list of processing jobs."""
    query = db.query(ProcessingJob)
    
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    jobs = (
        query.order_by(ProcessingJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jobs


@router.get("/courses/{course_id}/analysis", response_model=CourseAnalysisResponse)
async def get_course_analysis(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get AI-generated analysis for a course."""
    analysis = db.query(CourseAnalysis).filter(CourseAnalysis.course_id == course_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Course analysis not found")
    return analysis


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Perform semantic search across content chunks."""
    # TODO: Implement actual vector search with embeddings
    # For now, return basic text search as placeholder
    
    import time
    start_time = time.time()
    
    query = db.query(ContentChunk)
    
    # Filter by course IDs if provided
    if search_request.course_ids:
        query = query.filter(ContentChunk.course_id.in_(search_request.course_ids))
    
    # Basic text search (replace with vector search later)
    chunks = (
        query.filter(ContentChunk.chunk_text.ilike(f"%{search_request.query}%"))
        .limit(search_request.limit)
        .all()
    )
    
    # Convert to search results
    from app.api.schemas import SearchResult
    results = []
    for chunk in chunks:
        result = SearchResult(
            chunk_id=chunk.id,
            course_id=chunk.course_id,
            asset_id=chunk.asset_id,
            chunk_text=chunk.chunk_text,
            similarity_score=0.8,  # Placeholder - would come from vector similarity
            chunk_index=chunk.chunk_index
        )
        results.append(result)
    
    search_time = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=search_request.query,
        results=results,
        total_results=len(results),
        search_time_ms=search_time
    )


@router.get("/courses/{course_id}/stats")
async def get_course_stats(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get statistics for a course's content."""
    chunk_count = db.query(ContentChunk).filter(ContentChunk.course_id == course_id).count()
    
    if chunk_count == 0:
        raise HTTPException(status_code=404, detail="No content found for course")
    
    # Get total token count
    total_tokens = (
        db.query(ContentChunk.token_count)
        .filter(ContentChunk.course_id == course_id)
        .all()
    )
    total_token_count = sum(tokens[0] for tokens in total_tokens)
    
    # Get unique asset count
    asset_count = (
        db.query(ContentChunk.asset_id)
        .filter(ContentChunk.course_id == course_id)
        .distinct()
        .count()
    )
    
    return {
        "course_id": course_id,
        "total_chunks": chunk_count,
        "total_tokens": total_token_count,
        "unique_assets": asset_count,
        "avg_tokens_per_chunk": total_token_count / chunk_count if chunk_count > 0 else 0
    }
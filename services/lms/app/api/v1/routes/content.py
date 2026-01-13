"""Content routes that proxy to AI service."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.integrations.ai_service.client import get_ai_service_client
from app.db.deps import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/content", tags=["content"])


class SearchRequest(BaseModel):
    """Request model for content search."""
    query: str
    course_ids: Optional[List[UUID]] = None
    limit: int = 10
    similarity_threshold: float = 0.7


@router.get("/courses/{course_id}/chunks")
async def get_course_chunks(
    course_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get content chunks for a course (proxies to AI service)."""
    ai_client = get_ai_service_client()
    
    try:
        chunks = await ai_client.get_course_chunks(course_id, limit, offset)
        return chunks
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve content chunks")


@router.get("/assets/{asset_id}/chunks")
async def get_asset_chunks(
    asset_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get content chunks for an asset (proxies to AI service)."""
    ai_client = get_ai_service_client()
    
    try:
        chunks = await ai_client.get_asset_chunks(asset_id)
        return chunks
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve asset chunks")


@router.post("/search")
async def search_content(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """Search content across courses (proxies to AI service)."""
    ai_client = get_ai_service_client()
    
    try:
        results = await ai_client.search_content(
            query=search_request.query,
            course_ids=search_request.course_ids,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to search content")


@router.get("/courses/{course_id}/stats")
async def get_course_stats(
    course_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get content statistics for a course (proxies to AI service)."""
    ai_client = get_ai_service_client()
    
    try:
        stats = await ai_client.get_course_stats(course_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Course content not found")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve course stats")


@router.get("/courses/{course_id}/analysis")
async def get_course_analysis(
    course_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get AI analysis for a course (proxies to AI service)."""
    ai_client = get_ai_service_client()
    
    try:
        analysis = await ai_client.get_course_analysis(course_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Course analysis not found")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve course analysis")


@router.get("/courses/{course_id}/processing-status")
async def get_processing_status(
    course_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get AI processing status for a course (proxies to AI service)."""
    ai_client = get_ai_service_client()
    
    try:
        status = await ai_client.get_processing_status(course_id)
        if not status:
            raise HTTPException(status_code=404, detail="Processing status not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve processing status")
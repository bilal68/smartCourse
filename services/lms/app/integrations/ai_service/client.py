"""AI Service client for LMS integration."""

import httpx
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIServiceClient:
    """Client for communicating with AI service."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.AI_SERVICE_URL
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )
    
    async def get_course_chunks(
        self, 
        course_id: UUID, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get content chunks for a course from AI service."""
        try:
            response = await self.client.get(
                f"/api/v1/content/courses/{course_id}/chunks",
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get course chunks from AI service: {e}")
            return []
    
    async def get_asset_chunks(self, asset_id: UUID) -> List[Dict[str, Any]]:
        """Get content chunks for an asset from AI service."""
        try:
            response = await self.client.get(
                f"/api/v1/content/assets/{asset_id}/chunks"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get asset chunks from AI service: {e}")
            return []
    
    async def get_processing_status(self, course_id: UUID) -> Optional[Dict[str, Any]]:
        """Get processing status for a course from AI service."""
        try:
            response = await self.client.get(
                f"/api/v1/content/courses/{course_id}/processing-status"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get processing status from AI service: {e}")
            return None
    
    async def search_content(
        self,
        query: str,
        course_ids: Optional[List[UUID]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Search content across courses using AI service."""
        try:
            payload = {
                "query": query,
                "limit": limit,
                "similarity_threshold": similarity_threshold
            }
            if course_ids:
                payload["course_ids"] = [str(id) for id in course_ids]
            
            response = await self.client.post(
                "/api/v1/content/search",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to search content in AI service: {e}")
            return {"query": query, "results": [], "total_results": 0, "search_time_ms": 0}
    
    async def get_course_stats(self, course_id: UUID) -> Optional[Dict[str, Any]]:
        """Get content statistics for a course from AI service."""
        try:
            response = await self.client.get(
                f"/api/v1/content/courses/{course_id}/stats"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get course stats from AI service: {e}")
            return None
    
    async def get_course_analysis(self, course_id: UUID) -> Optional[Dict[str, Any]]:
        """Get AI analysis for a course from AI service."""
        try:
            response = await self.client.get(
                f"/api/v1/content/courses/{course_id}/analysis"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get course analysis from AI service: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_ai_client: Optional[AIServiceClient] = None


def get_ai_service_client() -> AIServiceClient:
    """Get the global AI service client."""
    global _ai_client
    if _ai_client is None:
        _ai_client = AIServiceClient()
    return _ai_client
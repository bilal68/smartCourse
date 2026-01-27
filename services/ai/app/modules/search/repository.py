"""Repository layer for search operations."""

import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text, or_

from app.modules.content.models import ContentChunk
from app.api.schemas import SearchRequest, SearchResponse, SearchResult
from app.core.logging import get_logger


class SearchRepository:
    """Repository for search operations."""
    
    def __init__(self, db: Session):
        self.db = db

    def semantic_search(
        self,
        query_embedding_str: str,
        model_name: str,
        similarity_threshold: float,
        limit: int,
        course_ids: Optional[List[str]] = None
    ) -> List[dict]:
        """Perform semantic search using pgvector cosine distance."""
        logger = get_logger(__name__)
        
        # Optional course filter
        course_filter_sql = ""
        params = {
            "query_embedding": query_embedding_str,
            "model_name": model_name,
            "threshold": float(similarity_threshold),
            "limit": int(limit),
        }

        if course_ids:
            # Convert course_ids to UUID array for PostgreSQL
            uuid_list = [str(cid) for cid in course_ids] 
            params["course_ids"] = uuid_list
            course_filter_sql = " AND cc.course_id::text = ANY(:course_ids)"
            logger.info(f"Filtering by course IDs: {params['course_ids']}")
        else:
            logger.info("No course filter applied - searching all courses")

        logger.info(
            f"Search params - model: {params['model_name']}, threshold: {params['threshold']}, limit: {params['limit']}"
        )

        # Semantic SQL using cosine distance (<=>). Similarity = 1 - distance
        similarity_query = text(f"""
            SELECT
                cc.id AS chunk_id,
                cc.course_id,
                cc.asset_id,
                cc.content,
                cc.chunk_index,
                (ce.embedding <=> (:query_embedding)::vector) AS distance,
                (1 - (ce.embedding <=> (:query_embedding)::vector)) AS similarity
            FROM content_chunks cc
            JOIN chunk_embeddings ce ON cc.id = ce.chunk_id
            WHERE ce.model_name = :model_name
              {course_filter_sql}
              AND (1 - (ce.embedding <=> (:query_embedding)::vector)) >= :threshold
            ORDER BY ce.embedding <=> (:query_embedding)::vector
            LIMIT :limit
        """)

        logger.info(f"Executing semantic SQL with {len(params)} parameters")
        rows = self.db.execute(similarity_query, params).mappings().all()
        logger.info(f"Found {len(rows)} results")

        return rows

    def text_search(
        self,
        query: str,
        course_ids: Optional[List[UUID]] = None,
        limit: int = 10
    ) -> List[ContentChunk]:
        """Fallback text search when embeddings are not available."""
        logger = get_logger(__name__)
        
        query_obj = self.db.query(ContentChunk)
        if course_ids:
            query_obj = query_obj.filter(ContentChunk.course_id.in_(course_ids))
        
        # Extract keywords from query for better text search
        import re
        query_text = query.lower()
        # Remove common words and extract meaningful terms
        keywords = re.findall(r'\\b[a-zA-Z]{3,}\\b', query_text)
        keywords = [k for k in keywords if k not in ['what', 'how', 'the', 'and', 'are', 'this', 'that', 'with']]
        
        logger.info(f"Text search query: '{query}' -> Keywords: {keywords}")
        
        if not keywords:
            keywords = [query_text.strip()]
        
        # Search for any of the keywords
        search_conditions = []
        for keyword in keywords:
            search_conditions.append(ContentChunk.content.ilike(f"%{keyword}%"))
        
        if search_conditions:
            chunks = (
                query_obj.filter(or_(*search_conditions))
                .limit(limit)
                .all()
            )
            logger.info(f"Found {len(chunks)} chunks matching keywords: {keywords}")
        else:
            chunks = []
            logger.warning(f"No search conditions generated for query: {query}")
        
        return chunks
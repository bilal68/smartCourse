"""Retrieval service for semantic search using pgvector."""
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from app.models.chunk_embedding import ChunkEmbedding
from app.models.content_chunk import ContentChunk
from app.services.embedding_service import get_embedding_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class RetrievalResult:
    """Result from semantic search."""
    def __init__(self, chunk_id: UUID, text: str, asset_id: UUID, score: float):
        self.chunk_id = chunk_id
        self.text = text
        self.asset_id = asset_id
        self.score = score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": str(self.chunk_id),
            "text": self.text,
            "asset_id": str(self.asset_id),
            "score": round(self.score, 4)
        }


class RetrievalService:
    """
    Service for semantic search using vector similarity.
    
    Uses cosine similarity with pgvector.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = get_embedding_service()
    
    def search(
        self,
        course_id: UUID,
        query: str,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Perform semantic search for query within course content.
        
        Args:
            course_id: Filter chunks by this course
            query: User question/query
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects sorted by similarity
        """
        # Generate embedding for query
        logger.info(f"Generating embedding for query: '{query[:50]}...'")
        query_embedding = self.embedding_service.create_embedding(query)
        
        # Perform vector similarity search
        # Using cosine distance (1 - cosine similarity)
        # Lower distance = higher similarity
        stmt = (
            select(
                ChunkEmbedding.chunk_id,
                ContentChunk.content,  # Use content field instead of chunk_text
                ContentChunk.asset_id,
                ChunkEmbedding.embedding.cosine_distance(query_embedding).label('distance')
            )
            .join(ContentChunk, ChunkEmbedding.chunk_id == ContentChunk.id)
            .where(ChunkEmbedding.course_id == course_id)
            .order_by(text('distance'))
            .limit(top_k)
        )
        
        results = self.db.execute(stmt).all()
        
        # Convert to RetrievalResult objects
        # Convert distance to similarity score (1 - distance)
        retrieval_results = [
            RetrievalResult(
                chunk_id=row.chunk_id,
                text=row.content,  # Use content field instead of chunk_text
                asset_id=row.asset_id,
                score=1.0 - row.distance  # Convert distance to similarity
            )
            for row in results
        ]
        
        logger.info(
            f"Retrieved {len(retrieval_results)} chunks for course_id={course_id}, "
            f"top_score={retrieval_results[0].score if retrieval_results else 0}"
        )
        
        return retrieval_results


def get_retrieval_service(db: Session) -> RetrievalService:
    """Factory function for dependency injection."""
    return RetrievalService(db)

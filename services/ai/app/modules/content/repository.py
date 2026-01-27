"""Repository layer for content chunk operations."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.modules.content.models import (
    ContentChunk,
    ChunkEmbedding,
    ProcessingJob,
    CourseAnalysis
)


class ContentChunkRepository:
    """Repository for ContentChunk entity with CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(
        self,
        course_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[ContentChunk]:
        """Get content chunks for a specific course."""
        return (
            self.db.query(ContentChunk)
            .filter(ContentChunk.course_id == course_id)
            .order_by(ContentChunk.chunk_index)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_by_asset_id(self, asset_id: UUID) -> List[ContentChunk]:
        """Get content chunks for a specific asset."""
        return (
            self.db.query(ContentChunk)
            .filter(ContentChunk.asset_id == asset_id)
            .order_by(ContentChunk.chunk_index)
            .all()
        )

    def get_chunks_without_embeddings(
        self,
        course_id: Optional[UUID] = None,
        model_name: Optional[str] = None
    ) -> List[ContentChunk]:
        """Get chunks that don't have embeddings."""
        query = (
            self.db.query(ContentChunk)
            .outerjoin(ChunkEmbedding, ContentChunk.id == ChunkEmbedding.chunk_id)
        )
        
        if model_name:
            query = query.filter(
                (ChunkEmbedding.id.is_(None)) | 
                (ChunkEmbedding.model_name != model_name)
            )
        else:
            query = query.filter(ChunkEmbedding.id.is_(None))
        
        if course_id:
            query = query.filter(ContentChunk.course_id == course_id)
            
        return query.all()

    def get_all_chunks(self, course_id: Optional[UUID] = None) -> List[ContentChunk]:
        """Get all chunks, optionally filtered by course."""
        query = self.db.query(ContentChunk)
        if course_id:
            query = query.filter(ContentChunk.course_id == course_id)
        return query.all()

    def get_course_stats(self, course_id: UUID) -> dict:
        """Get statistics for a course's content."""
        chunk_count = self.db.query(ContentChunk).filter(ContentChunk.course_id == course_id).count()
        
        if chunk_count == 0:
            return None
            
        # Get total token count
        total_tokens = (
            self.db.query(ContentChunk.token_count)
            .filter(ContentChunk.course_id == course_id)
            .all()
        )
        total_token_count = sum(tokens[0] for tokens in total_tokens if tokens[0])
        
        # Get unique asset count
        asset_count = (
            self.db.query(ContentChunk.asset_id)
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


class ProcessingJobRepository:
    """Repository for ProcessingJob entity."""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: UUID) -> Optional[ProcessingJob]:
        """Get processing job for a course."""
        return self.db.query(ProcessingJob).filter(ProcessingJob.course_id == course_id).first()

    def get_all(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProcessingJob]:
        """Get list of processing jobs."""
        query = self.db.query(ProcessingJob)
        
        if status:
            query = query.filter(ProcessingJob.status == status)
        
        return (
            query.order_by(ProcessingJob.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )


class CourseAnalysisRepository:
    """Repository for CourseAnalysis entity."""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: UUID) -> Optional[CourseAnalysis]:
        """Get AI-generated analysis for a course."""
        return self.db.query(CourseAnalysis).filter(CourseAnalysis.course_id == course_id).first()


class ChunkEmbeddingRepository:
    """Repository for ChunkEmbedding entity."""
    
    def __init__(self, db: Session):
        self.db = db

    def delete_by_chunk_ids(self, chunk_ids: List[UUID]) -> int:
        """Delete embeddings for specific chunks."""
        if not chunk_ids:
            return 0
            
        delete_query = self.db.query(ChunkEmbedding).filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        count = delete_query.count()
        delete_query.delete(synchronize_session=False)
        return count

    def bulk_create(self, embedding_mappings: List[dict]) -> int:
        """Bulk insert embeddings."""
        if not embedding_mappings:
            return 0
            
        self.db.bulk_insert_mappings(ChunkEmbedding, embedding_mappings)
        return len(embedding_mappings)
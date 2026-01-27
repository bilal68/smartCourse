"""Service layer for content operations."""

import time
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.content.repository import (
    ContentChunkRepository,
    ProcessingJobRepository,
    CourseAnalysisRepository,
    ChunkEmbeddingRepository
)
from app.modules.content.models import ContentChunk, ChunkEmbedding
from app.core.logging import get_logger


class ContentService:
    """Service layer for content operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.content_repo = ContentChunkRepository(db)
        self.processing_repo = ProcessingJobRepository(db)
        self.analysis_repo = CourseAnalysisRepository(db)
        self.embedding_repo = ChunkEmbeddingRepository(db)

    def get_course_chunks(
        self,
        course_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[ContentChunk]:
        """Get content chunks for a specific course."""
        return self.content_repo.get_by_course_id(course_id, limit, offset)

    def get_asset_chunks(self, asset_id: UUID) -> List[ContentChunk]:
        """Get content chunks for a specific asset."""
        return self.content_repo.get_by_asset_id(asset_id)

    def get_processing_status(self, course_id: UUID):
        """Get processing status for a course."""
        job = self.processing_repo.get_by_course_id(course_id)
        if not job:
            raise HTTPException(status_code=404, detail="Processing job not found")
        return job

    def get_processing_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ):
        """Get list of processing jobs."""
        return self.processing_repo.get_all(status, limit, offset)

    def get_course_analysis(self, course_id: UUID):
        """Get AI-generated analysis for a course."""
        analysis = self.analysis_repo.get_by_course_id(course_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Course analysis not found")
        return analysis

    def get_course_stats(self, course_id: UUID):
        """Get statistics for a course's content."""
        stats = self.content_repo.get_course_stats(course_id)
        if not stats:
            raise HTTPException(status_code=404, detail="No content found for course")
        return stats

    def generate_embeddings(
        self,
        course_id: Optional[UUID] = None,
        force_regenerate: bool = True
    ) -> dict:
        """Generate embeddings for content chunks using the configured provider."""
        from app.services.embedding_service import get_embedding_service
        
        logger = get_logger(__name__)
        
        if force_regenerate:
            # Get ALL chunks for the course (ignore existing embeddings)
            chunks_to_process = self.content_repo.get_all_chunks(course_id)
            
            # Delete existing embeddings
            if chunks_to_process:
                chunk_ids = [chunk.id for chunk in chunks_to_process]
                deleted_count = self.embedding_repo.delete_by_chunk_ids(chunk_ids)
                self.db.commit()
                logger.info(f"Deleted {deleted_count} existing embeddings")
        else:
            # Get chunks without embeddings only
            chunks_to_process = self.content_repo.get_chunks_without_embeddings(course_id)
        
        if not chunks_to_process:
            return {"message": "No chunks to process", "updated": 0}
        
        logger.info(f"Processing {len(chunks_to_process)} chunks (force_regenerate={force_regenerate})")
        
        # Initialize embedding service
        try:
            embedding_service = get_embedding_service()
            model_info = embedding_service.get_model_info()
            logger.info(f"Using {model_info['provider']} embeddings with model: {model_info['model_name']}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            
            # Check for common Windows PyTorch dependency issue
            if "c10.dll" in str(e) or "WinError 126" in str(e):
                detail = (
                    "PyTorch dependency missing. Please install Microsoft Visual C++ Redistributable:\\n"
                    "1. Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe\\n"
                    "2. Install and restart your terminal\\n"
                    "3. Try again"
                )
            else:
                detail = f"Embedding service initialization error: {str(e)}"
            
            raise HTTPException(status_code=500, detail=detail)
        
        updated_count = 0
        batch_size = 32
        
        try:
            # Process chunks in batches to manage memory
            for i in range(0, len(chunks_to_process), batch_size):
                batch = chunks_to_process[i:i + batch_size]
                batch_texts = [chunk.content for chunk in batch]
                
                logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} chunks")
                
                # Generate embeddings for the batch
                embeddings = embedding_service.encode(batch_texts)
                
                # Prepare bulk insert data
                embedding_mappings = []
                for chunk, embedding in zip(batch, embeddings):
                    embedding_mappings.append({
                        'id': uuid4(),
                        'chunk_id': chunk.id,
                        'course_id': chunk.course_id,
                        'embedding': embedding.tolist(),  # Convert numpy array to list
                        'model_name': model_info['model_name']
                    })
                
                # Bulk insert embeddings for better performance
                updated_count += self.embedding_repo.bulk_create(embedding_mappings)
                
                # Commit batch
                self.db.commit()
                logger.info(f"Stored {len(batch)} embeddings")
            
            return {
                "message": f"Generated {updated_count} embeddings using {model_info['provider']}",
                "updated": updated_count,
                "total_chunks": len(chunks_to_process),
                "provider": model_info['provider'],
                "model": model_info['model_name'],
                "force_regenerate": force_regenerate
            }
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")
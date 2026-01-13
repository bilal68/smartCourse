"""
DEPRECATED: Process course content and chunk it for search and retrieval.

This content processor is now handled by the AI service.
Content processing happens in the AI service when course.published events are received.
This file remains for backward compatibility.
"""

import re
import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.content_chunk import ContentChunk
from app.models.learning_asset import LearningAsset, AssetType
from app.integrations.s3 import get_s3_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContentProcessor:
    """
    Processes course content by reading from S3 and chunking for search.
    Handles different content types (videos, PDFs, articles) appropriately.
    """
    
    # Chunking configuration
    CHUNK_SIZE_WORDS = 500  # Target words per chunk
    CHUNK_OVERLAP_WORDS = 50  # Overlap between chunks for context
    
    def __init__(self, db: Session):
        self.db = db
        self.s3_client = get_s3_client()
    
    def process_asset(self, asset: LearningAsset) -> Dict[str, Any]:
        """
        Process a single learning asset - read content and create chunks.
        
        Args:
            asset: LearningAsset to process
            
        Returns:
            dict with processing summary
        """
        logger.info("Processing asset", asset_id=str(asset.id), asset_type=asset.asset_type.value)
        
        # Delete existing chunks for this asset (re-processing scenario)
        self.db.query(ContentChunk).filter(ContentChunk.asset_id == asset.id).delete()
        
        try:
            # Read content from S3
            if not asset.source_url:
                logger.warning("Asset has no source_url", asset_id=str(asset.id))
                return {"success": False, "error": "No source URL"}
            
            content = self._read_content_from_s3(asset.source_url)
            
            if not content:
                logger.warning("No content retrieved", asset_id=str(asset.id))
                return {"success": False, "error": "Empty content"}
            
            # Create chunks
            chunks = self._chunk_content(content, asset)
            
            # Store chunks in database
            chunk_count = self._store_chunks(asset.id, chunks)
            
            logger.info(
                "Asset processing complete",
                asset_id=str(asset.id),
                chunks_created=chunk_count,
                content_size=len(content)
            )
            
            return {
                "success": True,
                "chunks_created": chunk_count,
                "content_size": len(content),
                "asset_id": str(asset.id)
            }
            
        except Exception as e:
            logger.error(
                "Failed to process asset",
                asset_id=str(asset.id),
                error=str(e),
                exc_info=True
            )
            return {"success": False, "error": str(e)}
    
    def process_course_assets(self, course_id: uuid.UUID, assets: List[LearningAsset]) -> Dict[str, Any]:
        """
        Process all assets for a course.
        
        Args:
            course_id: Course ID
            assets: List of assets to process
            
        Returns:
            dict with overall processing summary
        """
        logger.info("Processing course assets", course_id=str(course_id), asset_count=len(assets))
        
        results = {
            "course_id": str(course_id),
            "total_assets": len(assets),
            "successful": 0,
            "failed": 0,
            "total_chunks": 0,
            "total_content_size": 0,
            "failed_assets": []
        }
        
        for asset in assets:
            result = self.process_asset(asset)
            
            if result.get("success"):
                results["successful"] += 1
                results["total_chunks"] += result.get("chunks_created", 0)
                results["total_content_size"] += result.get("content_size", 0)
            else:
                results["failed"] += 1
                results["failed_assets"].append({
                    "asset_id": str(asset.id),
                    "title": asset.title,
                    "error": result.get("error")
                })
        
        logger.info("Course assets processing complete", **results)
        return results
    
    def _read_content_from_s3(self, key: str) -> str:
        """
        Read content from S3 using the source URL key.
        
        Args:
            key: S3 key (source_url from asset)
            
        Returns:
            Content as string
        """
        try:
            content_bytes = self.s3_client.get_object(key)
            content = content_bytes.decode('utf-8')
            return content
        except Exception as e:
            logger.error("Failed to read from S3", key=key, error=str(e))
            raise
    
    def _chunk_content(self, content: str, asset: LearningAsset) -> List[Dict[str, Any]]:
        """
        Split content into overlapping chunks.
        
        Strategy:
        - Split by paragraphs first (double newlines)
        - Group paragraphs into ~500 word chunks
        - Add 50-word overlap between chunks for context
        - Calculate approximate token count (words * 1.3)
        
        Args:
            content: Text content to chunk
            asset: Asset metadata for context
            
        Returns:
            List of chunk dictionaries
        """
        # Clean and normalize content
        content = self._normalize_content(content)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
        
        chunks = []
        current_chunk_words = []
        current_word_count = 0
        
        for paragraph in paragraphs:
            para_words = paragraph.split()
            para_word_count = len(para_words)
            
            # If adding this paragraph exceeds chunk size, finalize current chunk
            if current_word_count > 0 and current_word_count + para_word_count > self.CHUNK_SIZE_WORDS:
                # Create chunk
                chunk_text = ' '.join(current_chunk_words)
                chunks.append({
                    "text": chunk_text,
                    "word_count": current_word_count,
                    "token_count": self._estimate_tokens(current_word_count)
                })
                
                # Start new chunk with overlap from previous chunk
                overlap_words = current_chunk_words[-self.CHUNK_OVERLAP_WORDS:] if len(current_chunk_words) > self.CHUNK_OVERLAP_WORDS else current_chunk_words
                current_chunk_words = overlap_words + para_words
                current_word_count = len(current_chunk_words)
            else:
                # Add paragraph to current chunk
                current_chunk_words.extend(para_words)
                current_word_count += para_word_count
        
        # Add final chunk if there's content
        if current_chunk_words:
            chunk_text = ' '.join(current_chunk_words)
            chunks.append({
                "text": chunk_text,
                "word_count": current_word_count,
                "token_count": self._estimate_tokens(current_word_count)
            })
        
        # If no chunks created (very short content), create one chunk
        if not chunks and content:
            words = content.split()
            chunks.append({
                "text": content,
                "word_count": len(words),
                "token_count": self._estimate_tokens(len(words))
            })
        
        logger.debug(
            "Content chunked",
            asset_id=str(asset.id),
            total_chunks=len(chunks),
            avg_chunk_size=sum(c["word_count"] for c in chunks) // len(chunks) if chunks else 0
        )
        
        return chunks
    
    def _normalize_content(self, content: str) -> str:
        """
        Normalize content - remove excessive whitespace, etc.
        """
        # Replace multiple spaces with single space
        content = re.sub(r' +', ' ', content)
        # Replace more than 2 newlines with 2 newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        # Strip leading/trailing whitespace
        content = content.strip()
        return content
    
    def _estimate_tokens(self, word_count: int) -> int:
        """
        Estimate token count from word count.
        Rough approximation: 1 word ≈ 1.3 tokens on average
        """
        return int(word_count * 1.3)
    
    def _store_chunks(self, asset_id: uuid.UUID, chunks: List[Dict[str, Any]]) -> int:
        """
        Store chunks in database.
        
        Args:
            asset_id: Asset ID
            chunks: List of chunk dictionaries
            
        Returns:
            Number of chunks stored
        """
        for index, chunk_data in enumerate(chunks):
            chunk = ContentChunk(
                asset_id=asset_id,
                chunk_index=index,
                chunk_text=chunk_data["text"],
                token_count=chunk_data["token_count"],
                extra={
                    "word_count": chunk_data["word_count"]
                }
            )
            self.db.add(chunk)
        
        self.db.commit()
        logger.debug("Chunks stored", asset_id=str(asset_id), count=len(chunks))
        
        return len(chunks)

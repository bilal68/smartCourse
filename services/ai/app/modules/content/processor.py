"""Content processing functionality."""

import re
import uuid
from typing import List, Dict, Any

from app.integrations.s3 import get_s3_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContentProcessor:
    """
    Processes course content by reading from S3 and chunking for search.
    Handles different content types (videos, PDFs, articles) appropriately.
    
    Now part of AI service for better architecture separation.
    """
    
    def __init__(self):
        self.s3_client = get_s3_client()
        # Convert character-based chunk size to approximate word count (avg 5 chars per word)
        self.chunk_size_words = settings.CHUNK_SIZE // 5
        self.chunk_overlap_words = settings.CHUNK_OVERLAP // 5
    
    def process_course_assets(self, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process all assets for a course.
        
        Args:
            course_data: Dict containing course_id and list of assets
                       {
                           "course_id": "uuid",
                           "assets": [
                               {
                                   "id": "uuid",
                                   "title": "Asset Title",
                                   "asset_type": "video",
                                   "source_url": "s3_key"
                               }
                           ]
                       }
            
        Returns:
            dict with processing summary
        """
        course_id = course_data["course_id"]
        assets = course_data["assets"]
        
        logger.info(f"Processing course assets, course_id={course_id}, asset_count={len(assets)}")
        
        results = {
            "course_id": course_id,
            "total_assets": len(assets),
            "successful": 0,
            "failed": 0,
            "total_chunks": 0,
            "total_content_size": 0,
            "failed_assets": [],
            "chunks_by_asset": {}
        }
        
        for asset in assets:
            try:
                asset_result = self.process_asset(asset)
                
                if asset_result.get("success"):
                    results["successful"] += 1
                    results["total_chunks"] += asset_result.get("chunks_created", 0)
                    results["total_content_size"] += asset_result.get("content_size", 0)
                    results["chunks_by_asset"][asset["id"]] = asset_result["chunks"]
                else:
                    results["failed"] += 1
                    results["failed_assets"].append({
                        "asset_id": asset["id"],
                        "title": asset["title"],
                        "error": asset_result.get("error")
                    })
                    
            except Exception as e:
                logger.error(
                    f"Unexpected error processing asset, asset_id={asset['id']}, error={str(e)}",
                    exc_info=True
                )
                results["failed"] += 1
                results["failed_assets"].append({
                    "asset_id": asset["id"],
                    "title": asset["title"],
                    "error": f"Unexpected error: {str(e)}"
                })
        
        logger.info(f"Course assets processing complete, course_id={course_id}, successful={results['successful']}, failed={results['failed']}")
        return results
    
    def process_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single learning asset - read content and create chunks.
        
        Args:
            asset: Asset dictionary with id, title, asset_type, source_url
            
        Returns:
            dict with processing summary including chunks
        """
        asset_id = asset["id"]
        logger.info(f"Processing asset, asset_id={asset_id}, asset_type={asset['asset_type']}")
        
        try:
            # Read content from S3
            source_url = asset.get("source_url")
            if not source_url:
                logger.warning(f"Asset has no source_url, asset_id={asset_id}")
                return {"success": False, "error": "No source URL"}
            
            content = self._read_content_from_s3(source_url)
            
            if not content:
                logger.warning(f"No content retrieved, asset_id={asset_id}")
                return {"success": False, "error": "Empty content"}
            
            # Create chunks
            chunks = self._chunk_content(content, asset)
            
            logger.info(
                f"Asset processing complete, asset_id={asset_id}, chunks_created={len(chunks)}, content_size={len(content)}"
            )
            
            return {
                "success": True,
                "chunks_created": len(chunks),
                "content_size": len(content),
                "asset_id": asset_id,
                "chunks": chunks  # Return actual chunks for storage by caller
            }
            
        except Exception as e:
            logger.error(
                f"Failed to process asset, asset_id={asset_id}, error={str(e)}",
                exc_info=True
            )
            return {"success": False, "error": str(e)}
    
    def _read_content_from_s3(self, key: str) -> str:
        """
        Read content from S3 using the source URL key.
        
        Args:
            key: S3 key (source_url from asset)
            
        Returns:
            Content as string
        """
        try:
            response = self.s3_client.get_object(key)
            # Handle both dict (DummyS3Client) and bytes (real S3) responses
            if isinstance(response, dict):
                content_bytes = response['Body']
            else:
                content_bytes = response
            content = content_bytes.decode('utf-8')
            return content
        except Exception as e:
            logger.error(f"Failed to read from S3, key={key}, error={str(e)}", exc_info=True)
            raise
    
    def _chunk_content(self, content: str, asset: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            if current_word_count > 0 and current_word_count + para_word_count > self.chunk_size_words:
                # Create chunk
                chunk_text = ' '.join(current_chunk_words)
                chunks.append({
                    "asset_id": asset["id"],
                    "chunk_index": len(chunks),
                    "chunk_text": chunk_text,
                    "word_count": current_word_count,
                    "token_count": self._estimate_tokens(current_word_count),
                    "extra": {
                        "asset_title": asset["title"],
                        "asset_type": asset["asset_type"]
                    }
                })
                
                # Start new chunk with overlap from previous chunk
                overlap_words = current_chunk_words[-self.chunk_overlap_words:] if len(current_chunk_words) > self.chunk_overlap_words else current_chunk_words
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
                "asset_id": asset["id"],
                "chunk_index": len(chunks),
                "chunk_text": chunk_text,
                "word_count": current_word_count,
                "token_count": self._estimate_tokens(current_word_count),
                "extra": {
                    "asset_title": asset["title"],
                    "asset_type": asset["asset_type"]
                }
            })
        
        # If no chunks created (very short content), create one chunk
        if not chunks and content:
            words = content.split()
            chunks.append({
                "asset_id": asset["id"],
                "chunk_index": 0,
                "chunk_text": content,
                "word_count": len(words),
                "token_count": self._estimate_tokens(len(words)),
                "extra": {
                    "asset_title": asset["title"],
                    "asset_type": asset["asset_type"]
                }
            })
        
        logger.debug(
            "Content chunked",
            asset_id=asset["id"],
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
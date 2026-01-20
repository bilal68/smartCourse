"""Chunking service for splitting text into manageable pieces."""
import re
from typing import List, Dict, Any
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    text: str
    chunk_index: int
    start_offset: int
    end_offset: int
    char_count: int


class ChunkingService:
    """
    Service for splitting text into overlapping chunks.
    
    Uses simple character-based chunking with optional overlap.
    For production, consider:
    - Sentence boundary detection
    - Paragraph-aware chunking  
    - Semantic chunking
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        
    def normalize_text(self, text: str) -> str:
        """
        Normalize text: strip, collapse whitespace, remove special chars.
        """
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Collapse multiple whitespaces/newlines into single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        return text
    
    def chunk_text(self, text: str, normalize: bool = True) -> List[TextChunk]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Raw text to chunk
            normalize: Whether to normalize text first
            
        Returns:
            List of TextChunk objects
        """
        if normalize:
            text = self.normalize_text(text)
        
        if not text:
            return []
        
        chunks: List[TextChunk] = []
        text_length = len(text)
        start = 0
        chunk_index = 0
        
        while start < text_length:
            # Calculate end position for this chunk
            end = min(start + self.chunk_size, text_length)
            
            # Extract chunk text
            chunk_text = text[start:end]
            
            # Skip empty chunks
            if chunk_text.strip():
                chunks.append(TextChunk(
                    text=chunk_text.strip(),
                    chunk_index=chunk_index,
                    start_offset=start,
                    end_offset=end,
                    char_count=len(chunk_text.strip())
                ))
                chunk_index += 1
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop if chunk_size < overlap
            if start <= (end - self.chunk_size):
                start = end
        
        logger.info(
            f"Created {len(chunks)} chunks from {text_length} chars "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        
        return chunks


def get_chunking_service() -> ChunkingService:
    """Factory function for dependency injection."""
    return ChunkingService()

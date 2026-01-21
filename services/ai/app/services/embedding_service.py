"""Embedding service for generating vector embeddings using OpenAI."""
import asyncio
from typing import List, Optional
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using OpenAI API.
    
    Includes retry logic and batch processing.
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.dimension = settings.OPENAI_EMBEDDING_DIMENSION
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            openai.OpenAIError: On API failure after retries
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # Validate dimension
            if len(embedding) != self.dimension:
                logger.warning(
                    f"Embedding dimension mismatch: expected {self.dimension}, "
                    f"got {len(embedding)}"
                )
            
            return embedding
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def create_embeddings_batch(
        self, 
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Create embeddings for multiple texts in batches.
        
        OpenAI allows up to ~2000 texts per request, but we use smaller batches
        for better error handling.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        all_embeddings: List[List[float]] = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )
                
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(
                    f"Created {len(batch_embeddings)} embeddings "
                    f"(batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1})"
                )
                
            except openai.OpenAIError as e:
                logger.error(f"Batch embedding failed for batch starting at {i}: {e}")
                raise
        
        logger.info(f"Created {len(all_embeddings)} embeddings total")
        return all_embeddings


def get_embedding_service() -> EmbeddingService:
    """Factory function for dependency injection."""
    return EmbeddingService()

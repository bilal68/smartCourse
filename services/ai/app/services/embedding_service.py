"""
Generic Embedding Service
Provider-agnostic service that works with any embedding provider
"""

import logging
from typing import List, Union
import numpy as np
from app.core.config import settings
from app.core.logging import get_logger
from app.services.embedding_providers import get_provider


class EmbeddingService:
    """
    Generic embedding service that works with any provider.
    Provider is determined by configuration, service code remains unchanged.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.provider = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the configured embedding provider."""
        try:
            provider_name = settings.EMBEDDING_PROVIDER
            self.logger.info(f"Initializing embedding provider: {provider_name}")
            
            # Get provider instance
            self.provider = get_provider(provider_name)
            
            # Initialize with configuration
            provider_config = {
                "model_name": settings.EMBEDDING_MODEL,
                "dimension": settings.EMBEDDING_DIMENSION,
            }
            
            # Add provider-specific config
            if provider_name == "sentence-transformers":
                provider_config["device"] = settings.EMBEDDING_DEVICE
            elif provider_name == "openai":
                provider_config["api_key"] = settings.OPENAI_API_KEY
            
            self.provider.initialize(**provider_config)
            self.logger.info(f"Provider {provider_name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding provider: {e}")
            raise
    
    
    def encode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """
        Generate embeddings for text(s) using the configured provider.
        
        Args:
            texts: Single text string or list of text strings
            **kwargs: Provider-specific parameters
            
        Returns:
            numpy array of embeddings with shape (n_texts, embedding_dimension)
        """
        if not self.provider:
            raise RuntimeError("Embedding provider not initialized")
        
        try:
            return self.provider.encode(texts, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def encode_query(self, query: str, **kwargs) -> np.ndarray:
        """
        Generate embedding for a search query.
        May include provider-specific query optimizations.
        
        Args:
            query: Search query string
            **kwargs: Provider-specific parameters
            
        Returns:
            numpy array of query embedding
        """
        if not self.provider:
            raise RuntimeError("Embedding provider not initialized")
        
        return self.provider.encode_query(query, **kwargs)
    
    def encode_document(self, document: str, **kwargs) -> np.ndarray:
        """
        Generate embedding for a document/content chunk.
        May include provider-specific document optimizations.
        
        Args:
            document: Document text to embed
            **kwargs: Provider-specific parameters
            
        Returns:
            numpy array of document embedding  
        """
        if not self.provider:
            raise RuntimeError("Embedding provider not initialized")
        
        return self.provider.encode_document(document, **kwargs)
    
    def get_dimension(self) -> int:
        """Get the embedding dimension of the current provider."""
        if not self.provider:
            raise RuntimeError("Embedding provider not initialized")
        
        return self.provider.get_dimension()
    
    def get_model_info(self) -> dict:
        """Get information about the current embedding provider."""
        if not self.provider:
            return {"provider": "not_initialized", "is_loaded": False}
        
        return self.provider.get_info()


# Global embedding service instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

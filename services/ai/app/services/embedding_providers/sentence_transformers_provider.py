"""
Sentence Transformers embedding provider
Local embedding generation using HuggingFace sentence-transformers
"""

from typing import List, Union
import numpy as np
from app.services.embedding_providers.base_provider import BaseEmbeddingProvider
from app.core.logging import get_logger


class SentenceTransformersProvider(BaseEmbeddingProvider):
    """Sentence Transformers implementation of embedding provider."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.model = None
        self.model_name = None
        self.dimension = None
        self.device = None
    
    def initialize(self, **kwargs) -> None:
        """Initialize the sentence transformers model."""
        try:
            # Import here to avoid dependency issues if not using this provider
            from sentence_transformers import SentenceTransformer
            
            self.model_name = kwargs.get("model_name", "multi-qa-MiniLM-L6-cos-v1")
            self.device = kwargs.get("device", "cpu")
            self.dimension = kwargs.get("dimension", 384)
            
            self.logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.logger.info(f"Model loaded successfully on {self.device}")
            
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
        except Exception as e:
            self.logger.error(f"Failed to initialize sentence-transformers: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings using sentence transformers."""
        if not self.model:
            raise RuntimeError("Provider not initialized. Call initialize() first.")
        
        if isinstance(texts, str):
            texts = [texts]
        
        batch_size = kwargs.get("batch_size", 32)
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            
            self.logger.info(f"Generated {len(texts)} embeddings, shape: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def encode_query(self, query: str, **kwargs) -> np.ndarray:
        """Encode query with Q&A optimization."""
        # Add query prefix for multi-qa models
        if "multi-qa" in self.model_name.lower():
            query = f"query: {query}"
        
        return self.encode(query, **kwargs)[0]
    
    def encode_document(self, document: str, **kwargs) -> np.ndarray:
        """Encode document with Q&A optimization."""
        # Add passage prefix for multi-qa models  
        if "multi-qa" in self.model_name.lower():
            document = f"passage: {document}"
        
        return self.encode(document, **kwargs)[0]
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.dimension
    
    def get_info(self) -> dict:
        """Get provider information."""
        return {
            "provider": "sentence-transformers",
            "model_name": self.model_name,
            "dimension": self.dimension,
            "device": self.device,
            "is_initialized": self.model is not None
        }
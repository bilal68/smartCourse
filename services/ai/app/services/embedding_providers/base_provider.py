"""
Base interface for embedding providers
All embedding providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def initialize(self, **kwargs) -> None:
        """Initialize the provider with configuration."""
        pass
    
    @abstractmethod
    def encode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """
        Encode texts into embeddings.
        
        Args:
            texts: Single text or list of texts to encode
            **kwargs: Provider-specific parameters
            
        Returns:
            numpy array of embeddings
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        pass
    
    @abstractmethod
    def get_info(self) -> dict:
        """Get provider information."""
        pass
    
    def encode_query(self, query: str, **kwargs) -> np.ndarray:
        """
        Encode a query for retrieval. Can be overridden for query-specific optimizations.
        
        Args:
            query: Query text
            **kwargs: Provider-specific parameters
            
        Returns:
            Query embedding as numpy array
        """
        return self.encode(query, **kwargs)[0] if isinstance(self.encode(query, **kwargs), np.ndarray) and len(self.encode(query, **kwargs).shape) > 1 else self.encode(query, **kwargs)
    
    def encode_document(self, document: str, **kwargs) -> np.ndarray:
        """
        Encode a document for indexing. Can be overridden for document-specific optimizations.
        
        Args:
            document: Document text
            **kwargs: Provider-specific parameters
            
        Returns:
            Document embedding as numpy array
        """
        return self.encode(document, **kwargs)[0] if isinstance(self.encode(document, **kwargs), np.ndarray) and len(self.encode(document, **kwargs).shape) > 1 else self.encode(document, **kwargs)
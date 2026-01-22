"""
Embedding providers package
Contains implementations for different embedding providers
"""

from .base_provider import BaseEmbeddingProvider
from .sentence_transformers_provider import SentenceTransformersProvider

# Provider registry
PROVIDERS = {
    "sentence-transformers": SentenceTransformersProvider,
}

def get_provider(provider_name: str) -> BaseEmbeddingProvider:
    """Get an embedding provider by name."""
    if provider_name not in PROVIDERS:
        raise ValueError(f"Unknown embedding provider: {provider_name}. Available: {list(PROVIDERS.keys())}")
    
    return PROVIDERS[provider_name]()
"""Service for generating and storing embeddings."""
from typing import List, Optional

from app.ai.embeddings import get_embedding_provider


class EmbeddingService:
    """Handles embedding generation using the configured provider."""
    
    def __init__(self):
        self.provider = get_embedding_provider()
    
    def embed(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text."""
        return self.provider.embed(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        return self.provider.embed_batch(texts)
    
    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        return self.provider.get_dimension()
    
    def is_available(self) -> bool:
        """Check if the embedding provider is available."""
        return self.provider.is_available()
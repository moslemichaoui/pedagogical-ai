"""Embedding provider abstraction for the Pedagogical AI platform."""
import hashlib
import os
from abc import ABC, abstractmethod
from typing import List, Optional

EMBEDDING_DIMENSION = 768
PLACEHOLDER_API_KEYS = {'', 'your-gemini-api-key-here'}


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


def _usable_gemini_key(api_key: Optional[str]) -> bool:
    return bool(api_key) and api_key.strip() not in PLACEHOLDER_API_KEYS


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embedding provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.model = model or os.environ.get('GEMINI_EMBEDDING_MODEL') or 'embedding-001'
        self._client = None
        self._dimension = EMBEDDING_DIMENSION

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not _usable_gemini_key(self.api_key):
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Please set the GEMINI_API_KEY environment variable."
            )

        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            return self._client
        except ImportError as e:
            raise RuntimeError(
                "google-genai package not installed. "
                "Please install it with: pip install google-genai"
            ) from e

    def embed(self, text: str) -> List[float]:
        client = self._get_client()
        try:
            response = client.models.embed_content(
                model=self.model,
                contents=text
            )
            values = list(response.embeddings[0].values)
            self._dimension = len(values)
            return values
        except Exception as e:
            # Fall back to mock embeddings if API fails
            import warnings
            warnings.warn(f"Gemini embedding API failed: {e}. Falling back to mock embeddings.")
            # Use the mock embedding logic inline
            import hashlib
            seed = hashlib.sha256((text or '').encode('utf-8')).digest()
            vector = []
            while len(vector) < EMBEDDING_DIMENSION:
                seed = hashlib.sha256(seed).digest()
                for i in range(0, len(seed), 4):
                    if len(vector) >= EMBEDDING_DIMENSION:
                        break
                    raw = int.from_bytes(seed[i:i + 4], 'big')
                    vector.append((raw / 0xFFFFFFFF) * 2 - 1)
            norm = sum(x * x for x in vector) ** 0.5
            if norm:
                vector = [x / norm for x in vector]
            return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        client = self._get_client()
        response = client.models.embed_content(
            model=self.model,
            contents=texts
        )
        vectors = [list(emb.values) for emb in response.embeddings]
        if vectors:
            self._dimension = len(vectors[0])
        return vectors

    def get_dimension(self) -> int:
        return self._dimension

    def is_available(self) -> bool:
        return _usable_gemini_key(self.api_key)


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing and development."""

    def embed(self, text: str) -> List[float]:
        seed = hashlib.sha256((text or '').encode('utf-8')).digest()
        vector = []
        while len(vector) < EMBEDDING_DIMENSION:
            seed = hashlib.sha256(seed).digest()
            for i in range(0, len(seed), 4):
                if len(vector) >= EMBEDDING_DIMENSION:
                    break
                raw = int.from_bytes(seed[i:i + 4], 'big')
                vector.append((raw / 0xFFFFFFFF) * 2 - 1)

        norm = sum(x * x for x in vector) ** 0.5
        if norm:
            vector = [x / norm for x in vector]
        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(text) for text in texts]

    def get_dimension(self) -> int:
        return EMBEDDING_DIMENSION

    def is_available(self) -> bool:
        return True


def get_embedding_provider() -> EmbeddingProvider:
    """Get Gemini embeddings when configured, otherwise a local mock."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if _usable_gemini_key(api_key):
        return GeminiEmbeddingProvider(api_key=api_key)
    return MockEmbeddingProvider()


def get_embedding_provider_safe() -> Optional[EmbeddingProvider]:
    try:
        return get_embedding_provider()
    except Exception:
        return None

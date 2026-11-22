"""Embedding facade used by ingestion and retrieval."""
from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from app.ai.embeddings import EmbeddingProvider, MockEmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Expose one embedding provider to the rest of the application."""

    def __init__(self, provider: Optional[EmbeddingProvider] = None, allow_mock: bool = False):
        self.provider = provider or get_embedding_provider(allow_mock=allow_mock)

    @property
    def available(self) -> bool:
        return self.provider is not None and self.provider.is_available()

    def require(self) -> EmbeddingProvider:
        if not self.available:
            raise RuntimeError(
                "لا يمكن فهرسة الوثائق دون مفتاح Gemini. أضف GEMINI_API_KEY ثم أعد المحاولة."
            )
        return self.provider  # type: ignore[return-value]

    def embed(self, text: str) -> List[float]:
        return self.require().embed(text)

    def embed_query(self, text: str) -> List[float]:
        provider = self.require()
        if hasattr(provider, "embed_query"):
            return provider.embed_query(text)  # type: ignore[no-any-return]
        return provider.embed(text)

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        return self.require().embed_batch(texts)

    def get_dimension(self) -> int:
        return self.require().get_dimension()

    def is_available(self) -> bool:
        return self.available

    @staticmethod
    def mock() -> "EmbeddingService":
        return EmbeddingService(provider=MockEmbeddingProvider())

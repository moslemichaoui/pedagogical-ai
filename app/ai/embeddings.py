"""Embedding providers backed by Google Gemini.

Embeddings are required for retrieval. When no key is configured the provider
reports itself unavailable instead of silently returning pseudo-random vectors,
so callers can degrade to lexical search with an honest message.
"""
from __future__ import annotations

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from app.utils.config_values import config_value

logger = logging.getLogger(__name__)

DEFAULT_DIMENSION = 768
MOCK_DIMENSION = 256


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be produced."""


class EmbeddingProvider(ABC):
    name = "base"
    requires_network = True

    @abstractmethod
    def embed(self, text: str) -> List[float]: ...

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        return [self.embed(text) for text in texts]

    @abstractmethod
    def get_dimension(self) -> int: ...

    @abstractmethod
    def is_available(self) -> bool: ...


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini embeddings with key rotation."""

    name = "gemini"

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        model: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        if api_keys is None or model is None:
            api_keys = config_value("GEMINI_API_KEYS") if api_keys is None else api_keys
            model = config_value("GEMINI_EMBEDDING_MODEL") if model is None else model
        self.api_keys = [key for key in (api_keys or []) if key]
        self.model = model or "text-embedding-004"
        self.timeout = timeout
        self._clients: dict[str, object] = {}
        self._dimension = DEFAULT_DIMENSION

    def _client(self, api_key: str):
        client = self._clients.get(api_key)
        if client is not None:
            return client
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise EmbeddingError("حزمة google-genai غير مثبّتة.") from exc
        options = None
        try:
            options = types.HttpOptions(timeout=self.timeout * 1000)
        except Exception:
            options = None
        try:
            client = genai.Client(api_key=api_key, http_options=options) if options else genai.Client(api_key=api_key)
        except TypeError:
            client = genai.Client(api_key=api_key)
        self._clients[api_key] = client
        return client

    def _call(self, texts: List[str], task_type: str) -> List[List[float]]:
        from google.genai import types

        last_error: Optional[Exception] = None
        for key in self.api_keys:
            try:
                client = self._client(key)
                config = None
                try:
                    config = types.EmbedContentConfig(task_type=task_type)
                except Exception:
                    config = None
                response = client.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config=config,
                )
                vectors = [list(item.values) for item in (response.embeddings or [])]
                if len(vectors) != len(texts):
                    raise EmbeddingError("عدد المتجهات لا يطابق عدد النصوص.")
                if vectors:
                    self._dimension = len(vectors[0])
                return vectors
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Embedding key failed: %s", str(exc)[:180])
                continue
        raise EmbeddingError(
            "تعذّر حساب التمثيلات الرقمية (embeddings). تحقّق من مفتاح Gemini."
        ) from last_error

    def embed(self, text: str) -> List[float]:
        return self._call([text or " "], "RETRIEVAL_DOCUMENT")[0]

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        items = [text or " " for text in texts]
        if not items:
            return []
        return self._call(items, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> List[float]:
        return self._call([text or " "], "RETRIEVAL_QUERY")[0]

    def get_dimension(self) -> int:
        return self._dimension

    def is_available(self) -> bool:
        return bool(self.api_keys)


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashed vectors, for tests only."""

    name = "mock"
    requires_network = False

    def embed(self, text: str) -> List[float]:
        digest = hashlib.sha256((text or "").encode("utf-8")).digest()
        raw: List[float] = []
        while len(raw) < MOCK_DIMENSION:
            digest = hashlib.sha256(digest).digest()
            for index in range(0, len(digest), 2):
                if len(raw) >= MOCK_DIMENSION:
                    break
                raw.append((int.from_bytes(digest[index : index + 2], "big") / 65535.0) * 2 - 1)
        norm = math.sqrt(sum(value * value for value in raw)) or 1.0
        return [value / norm for value in raw]

    def get_dimension(self) -> int:
        return MOCK_DIMENSION

    def is_available(self) -> bool:
        return True


def get_embedding_provider(allow_mock: bool = False) -> Optional[EmbeddingProvider]:
    """Return a real provider when configured, else a mock when allowed."""
    provider = GeminiEmbeddingProvider()
    if provider.is_available():
        return provider
    if allow_mock:
        return MockEmbeddingProvider()
    return None

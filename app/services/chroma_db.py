"""ChromaDB vector store wrapper.

Chroma is treated as a rebuildable index: SQLite remains the source of truth
for chunk text, so any vector-store failure degrades retrieval instead of
breaking the application.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

COLLECTION_NAME = "pedagogical_documents"
_lock = threading.Lock()


def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep only Chroma-compatible, non-empty metadata values."""
    cleaned: Dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            cleaned[key] = value
        elif isinstance(value, (int, float)):
            cleaned[key] = value
        elif isinstance(value, str):
            if value.strip():
                cleaned[key] = value.strip()
        else:
            cleaned[key] = str(value)
    return cleaned


def build_where_clause(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conditions = [{key: value} for key, value in filters.items() if value not in (None, "")]
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


class ChromaService:
    """Thin, defensive wrapper around a persistent Chroma collection."""

    def __init__(self, persist_dir: Optional[str] = None):
        if persist_dir is None:
            try:
                from flask import current_app

                persist_dir = current_app.config.get("CHROMA_PERSIST_DIR")
            except RuntimeError:
                persist_dir = None
            persist_dir = persist_dir or os.environ.get("CHROMA_PERSIST_DIR")
        self.persist_dir = persist_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "chromadb_data")
        )
        self._client = None
        self._collection = None

    # -- plumbing -----------------------------------------------------
    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        with _lock:
            if self._collection is not None:
                return self._collection
            try:
                import chromadb
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("حزمة chromadb غير مثبّتة.") from exc
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            try:
                self._collection = self._client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                    embedding_function=None,
                )
            except TypeError:
                self._collection = self._client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            return self._collection

    def reset(self) -> None:
        """Drop and recreate the collection (used after a failed reindex)."""
        try:
            client = self._get_collection()._client  # type: ignore[attr-defined]
        except Exception:
            client = None
        if client is not None:
            try:
                client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
        self._collection = None

    # -- writes -------------------------------------------------------
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        ids, documents, metadatas, embeddings = [], [], [], []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            embedding = chunk.get("embedding")
            if not chunk_id or embedding is None:
                raise ValueError("كل مقطع يحتاج إلى chunk_id و embedding.")
            metadata = sanitize_metadata(chunk.get("metadata"))
            metadata.setdefault("chunk_id", str(chunk_id))
            ids.append(str(chunk_id))
            documents.append(chunk.get("text", ""))
            metadatas.append(metadata)
            embeddings.append(list(embedding))
        self._get_collection().upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(ids)

    def delete_document(self, document_id: int) -> bool:
        try:
            collection = self._get_collection()
            collection.delete(where={"document_id": int(document_id)})
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chroma delete failed for document %s: %s", document_id, exc)
            return False

    # -- reads --------------------------------------------------------
    def search(
        self,
        query_vector: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            collection = self._get_collection()
            count = collection.count()
            if count == 0:
                return []
            kwargs: Dict[str, Any] = {
                "query_embeddings": [query_vector],
                "n_results": min(max(1, n_results), count),
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                kwargs["where"] = where
            results = collection.query(**kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chroma search failed: %s", exc)
            return []

        formatted: List[Dict[str, Any]] = []
        documents = (results or {}).get("documents") or []
        if not documents:
            return []
        metadatas = results.get("metadatas") or [[]]
        distances = results.get("distances") or [[]]
        for index, document in enumerate(documents[0]):
            metadata = metadatas[0][index] if metadatas and metadatas[0] else {}
            distance = distances[0][index] if distances and distances[0] else 1.0
            formatted.append(
                {
                    "text": document or "",
                    "metadata": metadata or {},
                    "distance": float(distance),
                    "similarity": max(0.0, 1.0 - float(distance)),
                }
            )
        return formatted

    def get_by_metadata(
        self, where: Optional[Dict[str, Any]] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        try:
            collection = self._get_collection()
            kwargs: Dict[str, Any] = {"include": ["documents", "metadatas"]}
            if where:
                kwargs["where"] = where
            if limit:
                kwargs["limit"] = limit
            results = collection.get(**kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chroma metadata query failed: %s", exc)
            return []
        documents = (results or {}).get("documents") or []
        metadatas = results.get("metadatas") or []
        return [
            {"text": document or "", "metadata": (metadatas[i] if i < len(metadatas) else {}) or {}}
            for i, document in enumerate(documents)
        ]

    def count(self) -> int:
        try:
            return int(self._get_collection().count())
        except Exception:
            return 0

    def health(self) -> Dict[str, Any]:
        try:
            return {
                "status": "healthy",
                "chunks": self.count(),
                "collection": COLLECTION_NAME,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector index health check failed: %s", exc)
            return {"status": "unhealthy", "error": "فهرس المتجهات غير متاح حالياً."}

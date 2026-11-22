"""Retrieval over the document index.

Semantic search is the primary path. When embeddings are unavailable, or when
the vector index returns nothing, retrieval falls back to a transparent
lexical ranking over SQLite so a teacher still gets useful sources.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional

from app.models import Document, DocumentChunk
from app.services.chroma_db import ChromaService
from app.services.embedding_service import EmbeddingService
from app.utils.config_values import config_value
from app.utils.text import normalize_arabic

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
_STOPWORDS = {
    "من", "في", "على", "عن", "إلى", "الى", "مع", "هذا", "هذه", "ذلك", "التي",
    "الذي", "ما", "لا", "أن", "ان", "كان", "كانت", "هو", "هي", "ثم", "أو",
    "او", "كل", "بعض", "بين", "بعد", "قبل", "كيف", "لماذا", "درس", "وحدة",
}


def _terms(text: str) -> List[str]:
    return [
        term
        for term in (normalize_arabic(word) for word in _WORD.findall(text or ""))
        if len(term) > 2 and term not in _STOPWORDS
    ]


class RetrievalService:
    """Combine vector similarity with metadata filters and a lexical fallback."""

    def __init__(
        self,
        chroma_service: Optional[ChromaService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.chroma_service = chroma_service or ChromaService()
        self.embedding_service = embedding_service or EmbeddingService()

    # -- public -------------------------------------------------------
    def retrieve(
        self,
        *,
        subject: Optional[str] = None,
        educational_level: Optional[str] = None,
        topic: Optional[str] = None,
        language: Optional[str] = None,
        n_results: int = 6,
        document_ids: Optional[Iterable[int]] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(n_results or config_value("RAG_TOP_K")), 20))
        threshold = config_value("RAG_MIN_SIMILARITY") if min_similarity is None else min_similarity
        ids = [int(item) for item in (document_ids or []) if str(item).isdigit()]

        results = self._semantic(
            subject=subject,
            educational_level=educational_level,
            topic=topic,
            language=language,
            limit=limit,
            document_ids=ids,
            threshold=threshold,
        )
        if len(results) < limit:
            results = self._merge(
                results,
                self._lexical(
                    subject=subject,
                    educational_level=educational_level,
                    topic=topic,
                    language=language,
                    limit=limit,
                    document_ids=ids,
                ),
                limit,
            )
        return results[:limit]

    # -- semantic -----------------------------------------------------
    def _semantic(
        self,
        *,
        subject: Optional[str],
        educational_level: Optional[str],
        topic: Optional[str],
        language: Optional[str],
        limit: int,
        document_ids: List[int],
        threshold: float,
    ) -> List[Dict[str, Any]]:
        query = (topic or "").strip()
        if not query or not self.embedding_service.is_available():
            return []
        try:
            vector = self.embedding_service.embed_query(query)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Query embedding failed, using lexical fallback: %s", exc)
            return []

        where = self._where(subject, educational_level, language, document_ids)
        try:
            hits = self.chroma_service.search(vector, n_results=limit * 3, where=where)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector search failed: %s", exc)
            return []

        filtered = [hit for hit in hits if hit.get("similarity", 0) >= threshold]
        if not filtered:
            filtered = hits[:limit]
        return self._decorate(filtered, limit)

    # -- lexical ------------------------------------------------------
    def _lexical(
        self,
        *,
        subject: Optional[str],
        educational_level: Optional[str],
        topic: Optional[str],
        language: Optional[str],
        limit: int,
        document_ids: List[int],
    ) -> List[Dict[str, Any]]:
        query_terms = set(_terms(topic or ""))
        query = (
            DocumentChunk.query.join(Document)
            .filter(Document.status.in_(["ready", "processing"]))
        )
        if subject:
            query = query.filter(DocumentChunk.subject == subject)
        if educational_level:
            query = query.filter(DocumentChunk.educational_level == educational_level)
        if language:
            query = query.filter(DocumentChunk.language == language)
        if document_ids:
            query = query.filter(DocumentChunk.document_id.in_(document_ids))
        rows = query.limit(400).all()

        scored: List[tuple[float, DocumentChunk]] = []
        for row in rows:
            if not query_terms:
                scored.append((0.1, row))
                continue
            haystack = normalize_arabic(row.text)
            overlap = sum(1 for term in query_terms if term in haystack)
            if overlap:
                scored.append((overlap / len(query_terms), row))
        scored.sort(key=lambda item: item[0], reverse=True)

        results = []
        for score, row in scored[:limit]:
            document = row.document
            results.append(
                {
                    "text": row.text,
                    "similarity": round(min(0.99, 0.35 + score * 0.5), 4),
                    "metadata": {
                        "chunk_id": row.chunk_id,
                        "document_id": row.document_id,
                        "filename": document.title if document else "وثيقة",
                        "source_type": document.source_type if document else None,
                        "subject": row.subject,
                        "educational_level": row.educational_level,
                        "language": row.language,
                        "page_number": row.page_number,
                    },
                    "retriever": "lexical",
                }
            )
        return results

    # -- helpers ------------------------------------------------------
    @staticmethod
    def _where(
        subject: Optional[str],
        educational_level: Optional[str],
        language: Optional[str],
        document_ids: List[int],
    ) -> Optional[Dict[str, Any]]:
        conditions: List[Dict[str, Any]] = []
        if subject:
            conditions.append({"subject": subject})
        if educational_level:
            conditions.append({"educational_level": educational_level})
        if language:
            conditions.append({"language": language})
        if document_ids:
            conditions.append({"document_id": {"$in": document_ids}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def _merge(
        primary: List[Dict[str, Any]], secondary: List[Dict[str, Any]], limit: int
    ) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for item in [*primary, *secondary]:
            metadata = item.get("metadata") or {}
            key = str(metadata.get("chunk_id") or (item.get("text") or "")[:60])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= limit:
                break
        return merged

    def _decorate(self, hits: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for hit in hits[:limit]:
            metadata = dict(hit.get("metadata") or {})
            metadata.setdefault("filename", "وثيقة مرجعية")
            results.append(
                {
                    "text": hit.get("text", ""),
                    "similarity": round(float(hit.get("similarity", 0.0)), 4),
                    "metadata": metadata,
                    "retriever": "vector",
                }
            )
        return results

    def stats(self) -> Dict[str, Any]:
        return {
            "documents": Document.query.filter_by(status="ready").count(),
            "chunks": DocumentChunk.query.count(),
            "vector_index": self.chroma_service.health(),
            "embeddings_available": self.embedding_service.is_available(),
        }

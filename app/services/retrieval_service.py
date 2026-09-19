"""Service for retrieving relevant chunks based on metadata and similarity."""
from typing import List, Dict, Any, Optional

from app.services.chroma_db import ChromaService, build_where_clause
from app.services.embedding_service import EmbeddingService


class RetrievalService:
    """Service for retrieving relevant chunks based on query criteria."""

    def __init__(self):
        self.chroma_service = ChromaService()
        self.embedding_service = EmbeddingService()

    def retrieve(
        self,
        subject: Optional[str] = None,
        educational_level: Optional[str] = None,
        topic: Optional[str] = None,
        language: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        results = self._retrieve_by_metadata(
            subject=subject,
            educational_level=educational_level,
            language=language,
            limit=n_results
        )

        if len(results) < n_results:
            semantic_results = self._retrieve_by_semantics(
                topic=topic if topic else subject,
                language=language,
                limit=n_results
            )
            seen_ids = set()
            merged = []
            for item in results + semantic_results:
                chunk_id = self._chunk_identity(item)
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)
                merged.append(item)
                if len(merged) >= n_results:
                    break
            results = merged

        return results[:n_results]

    def _chunk_identity(self, item: Dict[str, Any]) -> str:
        metadata = item.get('metadata') or {}
        return str(metadata.get('chunk_id') or item.get('text', '')[:80])

    def _retrieve_by_metadata(
        self,
        subject: Optional[str] = None,
        educational_level: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        where = build_where_clause({
            'subject': subject,
            'educational_level': educational_level,
            'language': language,
        })
        if not where:
            return []

        try:
            results = self.chroma_service.get_by_metadata(where=where, limit=limit)
            return results[:limit]
        except Exception:
            return []

    def _retrieve_by_semantics(
        self,
        topic: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not topic:
            return []

        embedding = self.embedding_service.embed(topic)
        results = self.chroma_service.search(
            query_vector=embedding,
            n_results=max(limit, 5),
        )

        if not language:
            return results[:limit]

        filtered = []
        for item in results:
            meta = item.get('metadata') or {}
            stored_language = meta.get('language')
            if stored_language in (None, '', language):
                filtered.append(item)
        return filtered[:limit]

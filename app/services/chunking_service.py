"""Arabic-aware text chunking for retrieval."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

from app.utils.config_values import config_value
from app.utils.text import clean_text

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟؛:])\s+|\n{2,}")


class ChunkingService:
    """Split long Arabic/French text into overlapping, sentence-aligned chunks."""

    def __init__(self, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        if chunk_size is None or overlap is None:
            chunk_size = config_value("CHUNK_SIZE") if chunk_size is None else chunk_size
            overlap = config_value("CHUNK_OVERLAP") if overlap is None else overlap
        self.chunk_size = max(120, chunk_size)
        self.overlap = max(0, min(overlap, self.chunk_size // 2))

    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any],
        start_index: int = 0,
    ) -> List[Dict[str, Any]]:
        text = clean_text(text)
        if not text:
            return []

        pieces = [piece.strip() for piece in _SENTENCE_SPLIT.split(text) if piece.strip()]
        if not pieces:
            pieces = [text]

        chunks: List[Dict[str, Any]] = []
        buffer = ""
        for piece in pieces:
            if len(piece) > self.chunk_size * 2:
                # Very long paragraph: hard-wrap it first.
                for start in range(0, len(piece), self.chunk_size):
                    self._flush(buffer, chunks, metadata, start_index)
                    buffer = ""
                    chunks.append(
                        self._build_chunk(
                            piece[start : start + self.chunk_size],
                            metadata,
                            start_index + len(chunks),
                            start,
                        )
                    )
                continue
            candidate = f"{buffer} {piece}".strip() if buffer else piece
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue
            self._flush(buffer, chunks, metadata, start_index)
            tail = self._tail(buffer)
            buffer = f"{tail} {piece}".strip() if tail else piece

        self._flush(buffer, chunks, metadata, start_index)
        return chunks

    def _flush(
        self,
        buffer: str,
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        start_index: int,
    ) -> None:
        if buffer.strip():
            chunks.append(
                self._build_chunk(buffer, metadata, start_index + len(chunks), 0)
            )

    def _tail(self, text: str) -> str:
        if not self.overlap or not text:
            return ""
        tail = text[-self.overlap :]
        # Start at a word boundary so the overlap reads naturally.
        space = tail.find(" ")
        if 0 <= space < len(tail) - 10:
            tail = tail[space + 1 :]
        return tail.strip()

    def _build_chunk(
        self,
        text: str,
        metadata: Dict[str, Any],
        index: int,
        start_char: int,
    ) -> Dict[str, Any]:
        cleaned = clean_text(text)
        chunk_metadata = {key: value for key, value in metadata.items() if value is not None}
        document_id = metadata.get("document_id", metadata.get("doc_id", 0))
        page_number = metadata.get("page_number")
        chunk_id = self._generate_chunk_id(document_id, index, page_number)
        chunk_metadata["chunk_id"] = chunk_id
        chunk_metadata["chunk_index"] = index
        return {
            "chunk_id": chunk_id,
            "chunk_index": index,
            "text": cleaned,
            "start_char": start_char,
            "end_char": start_char + len(cleaned),
            "metadata": chunk_metadata,
        }

    @staticmethod
    def _generate_chunk_id(doc_id: Any, chunk_index: int, page_number: Any = None) -> str:
        payload = f"{doc_id}:{page_number}:{chunk_index}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

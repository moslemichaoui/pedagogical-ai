"""Service for text chunking with configurable size and overlap."""
import hashlib
import re
from typing import List, Dict, Any


class ChunkingService:
    """Handles text chunking for RAG with configurable parameters."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: Dict[str, Any], start_index: int = 0) -> List[Dict[str, Any]]:
        """Split text into chunks preserving metadata."""
        if not text or not text.strip():
            return []

        text = text.strip()
        sentences = re.split(r'(?<=[.!?؟])\s+', text)

        chunks = []
        current_chunk = ""
        current_start = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(self._build_chunk(
                    current_chunk,
                    metadata,
                    start_index + len(chunks),
                    current_start,
                ))
                overlap_text = self._get_overlap(current_chunk)
                current_start = current_start + len(current_chunk) - len(overlap_text)
                current_chunk = (overlap_text + " " + sentence).strip()
            else:
                if current_chunk:
                    current_chunk += " "
                current_chunk += sentence

        if current_chunk.strip():
            chunks.append(self._build_chunk(
                current_chunk,
                metadata,
                start_index + len(chunks),
                current_start,
            ))

        return chunks

    def _build_chunk(self, text: str, metadata: Dict[str, Any], index: int, start_char: int) -> Dict[str, Any]:
        cleaned = text.strip()
        chunk_metadata = {k: v for k, v in metadata.items() if v is not None}
        chunk_id = self._generate_chunk_id(
            metadata.get('document_id', metadata.get('doc_id', 0)),
            index,
            metadata.get('page_number'),
        )
        chunk_metadata['chunk_id'] = chunk_id
        return {
            'chunk_id': chunk_id,
            'text': cleaned,
            'start_char': start_char,
            'end_char': start_char + len(cleaned),
            'metadata': chunk_metadata,
        }

    def _generate_chunk_id(self, doc_id: int, chunk_index: int, page_number=None) -> str:
        content = f"{doc_id}:{page_number}:{chunk_index}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_overlap(self, text: str) -> str:
        if len(text) <= self.overlap:
            return text
        return text[-self.overlap:]

"""Service for handling document ingestion, extraction, and indexing."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import db
from app.models import Document, DocumentChunk
from app.services.chunking_service import ChunkingService
from app.services.chroma_db import ChromaService, sanitize_metadata
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import ExtractionService

SOURCE_TYPES = {'official', 'teacher_upload', 'web'}
DEFAULT_SOURCE_TYPE = 'teacher_upload'


class DocumentService:
    """Handles document upload, extraction, chunking, embedding, and indexing."""

    SUPPORTED_EXTENSIONS = ExtractionService.SAFE_EXTENSIONS
    MAX_FILE_SIZE = ExtractionService.MAX_FILE_SIZE

    def __init__(self):
        self.extraction_service = ExtractionService()
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.chroma_service = ChromaService()

    def ingest(
        self,
        file_path: str,
        filename: Optional[str] = None,
        source_type: str = DEFAULT_SOURCE_TYPE,
        subject: Optional[str] = None,
        educational_level: Optional[str] = None,
        language: Optional[str] = 'ar',
        chapter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the full RAG ingestion pipeline for one file."""
        source_type = (source_type or DEFAULT_SOURCE_TYPE).strip()
        if source_type not in SOURCE_TYPES:
            raise ValueError(
                f"Invalid source_type '{source_type}'. Expected one of: {sorted(SOURCE_TYPES)}"
            )

        validation = self.extraction_service.validate_file(file_path)
        if not validation['valid']:
            raise ValueError(validation['error'])

        extracted = self.extraction_service.extract_text(file_path)
        if extracted.get('error'):
            raise ValueError(extracted['error'])

        text_content = (extracted.get('text') or '').strip()
        if not text_content:
            raise ValueError('No extractable text found in document')

        display_name = filename or Path(file_path).name
        pages = extracted.get('pages') or []
        language = language or extracted.get('language') or 'ar'
        subject = subject or extracted.get('subject')
        educational_level = educational_level or extracted.get('level')
        chapter = chapter or extracted.get('chapter')

        document = None
        chroma_written = False
        try:
            document = Document(
                title=Path(display_name).stem or Path(file_path).stem,
                file_path=str(file_path),
                source_type=source_type,
                text_content=text_content,
                page_numbers=", ".join(map(str, pages)) if pages else None,
                subject=subject,
                educational_level=educational_level,
                language=language,
                chapter=chapter,
                created_at=datetime.utcnow(),
            )
            db.session.add(document)
            db.session.flush()

            chunks = self._chunk_extracted_text(
                extracted,
                document_id=document.id,
                filename=display_name,
                source_type=source_type,
                subject=subject,
                educational_level=educational_level,
                language=language,
                chapter=chapter,
            )
            if not chunks:
                raise ValueError('Chunking produced no chunks')

            embeddings = self.embedding_service.embed_batch([chunk['text'] for chunk in chunks])
            if len(embeddings) != len(chunks):
                raise RuntimeError('Embedding count does not match chunk count')
            expected_dim = self.embedding_service.get_dimension()
            for vector in embeddings:
                if len(vector) != expected_dim:
                    raise RuntimeError(
                        f'Embedding dimension mismatch: expected {expected_dim}, got {len(vector)}'
                    )

            chroma_payload = []
            for chunk, vector in zip(chunks, embeddings):
                metadata = sanitize_metadata(chunk['metadata'])
                page_number = metadata.get('page_number')
                db.session.add(DocumentChunk(
                    document_id=document.id,
                    chunk_id=chunk['chunk_id'],
                    text=chunk['text'],
                    page_number=page_number if isinstance(page_number, int) else None,
                    subject=subject,
                    educational_level=educational_level,
                    language=language,
                    created_at=datetime.utcnow(),
                ))
                chroma_payload.append({
                    'chunk_id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'embedding': vector,
                    'metadata': metadata,
                })

            self.chroma_service.add_chunks(chroma_payload)
            chroma_written = True
            db.session.commit()
        except Exception:
            db.session.rollback()
            if chroma_written and document is not None and document.id:
                try:
                    self.chroma_service.delete_document(document.id)
                except Exception:
                    pass
            raise

        return {
            'success': True,
            'document_id': document.id,
            'filename': display_name,
            'number_of_chunks': len(chunks),
            'source_type': source_type,
            'message': 'Document ingested successfully',
        }

    def upload(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Backwards-compatible alias for ingest()."""
        return self.ingest(file_path, **kwargs)

    def list_documents(self) -> List[Dict[str, Any]]:
        documents = Document.query.order_by(Document.id.desc()).all()
        results = []
        for document in documents:
            suffix = Path(document.file_path).suffix
            filename = f"{document.title}{suffix}"
            results.append({
                'document_id': document.id,
                'title': document.title,
                'filename': filename,
                'file_type': suffix.lstrip('.').upper() or None,
                'source_type': document.source_type,
                'subject': document.subject,
                'educational_level': document.educational_level,
                'language': document.language,
                'chapter': document.chapter,
                'created_at': document.created_at.isoformat() if document.created_at else None,
                'processing_status': 'processed' if document.chunks else 'pending',
                'number_of_chunks': len(document.chunks),
            })
        return results

    def _chunk_extracted_text(
        self,
        extracted: Dict[str, Any],
        document_id: int,
        filename: str,
        source_type: str,
        subject: Optional[str],
        educational_level: Optional[str],
        language: Optional[str],
        chapter: Optional[str],
    ) -> List[Dict[str, Any]]:
        page_texts = extracted.get('page_texts') or []
        if not page_texts:
            page_texts = [{'page_number': 1, 'text': extracted.get('text') or ''}]

        all_chunks = []
        for page in page_texts:
            page_metadata = {
                'document_id': document_id,
                'filename': filename,
                'source_type': source_type,
                'subject': subject,
                'educational_level': educational_level,
                'language': language,
                'chapter': chapter,
                'page_number': page.get('page_number'),
            }
            page_chunks = self.chunking_service.chunk(
                page.get('text') or '',
                page_metadata,
                start_index=len(all_chunks),
            )
            all_chunks.extend(page_chunks)
        return all_chunks

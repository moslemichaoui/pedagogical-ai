"""Document ingestion, listing and deletion."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import db
from app.models import Document, DocumentChunk
from app.services.chunking_service import ChunkingService
from app.services.chroma_db import ChromaService, sanitize_metadata
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)

SOURCE_TYPES = {"official", "teacher_upload", "web"}
DEFAULT_SOURCE_TYPE = "teacher_upload"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def safe_error_message(exc: Exception) -> str:
    """Return a client-safe Arabic message; log internals instead of leaking them.

    ``DocumentError`` messages are authored by us, so they are safe to show.
    Anything else may contain library internals or filesystem paths.
    """
    if isinstance(exc, DocumentError):
        return str(exc)[:1000]
    logger.warning("Document operation failed: %s", exc)
    return "تعذّر معالجة الوثيقة. تحقّق من صحتها ثم أعد المحاولة."


class DocumentError(ValueError):
    """An ingestion problem with an Arabic message and a stable code."""

    def __init__(self, message: str, code: str = "document_error"):
        super().__init__(message)
        self.code = code


class DocumentService:
    """Own the document lifecycle: extract → chunk → embed → index."""

    def __init__(self):
        self.extraction = ExtractionService()
        self.chunking = ChunkingService()
        self.embeddings = EmbeddingService()
        self.chroma = ChromaService()

    # -- ingestion ----------------------------------------------------
    def ingest(
        self,
        file_path: str,
        *,
        filename: Optional[str] = None,
        source_type: str = DEFAULT_SOURCE_TYPE,
        subject: Optional[str] = None,
        educational_level: Optional[str] = None,
        language: str = "ar",
        chapter: Optional[str] = None,
    ) -> Dict[str, Any]:
        source_type = (source_type or DEFAULT_SOURCE_TYPE).strip()
        if source_type not in SOURCE_TYPES:
            raise DocumentError("نوع المصدر غير معروف.", "invalid_source_type")

        checksum = self.extraction.checksum(file_path)
        existing = Document.query.filter_by(checksum=checksum).first()
        if existing is not None:
            return {
                "success": True,
                "duplicate": True,
                "document_id": existing.id,
                "title": existing.title,
                "number_of_chunks": existing.chunk_count or len(existing.chunks),
                "message": "هذه الوثيقة موجودة مسبقاً في قاعدة المعرفة.",
            }

        validation = self.extraction.validate_file(file_path)
        if not validation["valid"]:
            raise DocumentError(validation["error"], "invalid_file")

        extracted = self.extraction.extract_text(file_path)
        if extracted.get("error"):
            raise DocumentError(extracted["error"], "extraction_failed")
        text = (extracted.get("text") or "").strip()
        if not text:
            raise DocumentError("لم يُستخرج أي نص من الوثيقة.", "empty_document")

        display_name = filename or Path(file_path).name
        guessed = self.extraction.guess_metadata(display_name)
        document = Document(
            title=Path(display_name).stem[:250] or "وثيقة",
            file_path=str(file_path),
            source_type=source_type,
            text_content=text,
            page_numbers=", ".join(str(page) for page in extracted.get("pages") or []),
            subject=subject or guessed.get("subject"),
            educational_level=educational_level or guessed.get("level"),
            language=language or "ar",
            chapter=chapter,
            checksum=checksum,
            file_size=os.path.getsize(file_path),
            status="processing",
            created_at=_now(),
        )
        db.session.add(document)
        db.session.flush()

        try:
            chunks = self._build_chunks(
                extracted,
                document_id=document.id,
                filename=display_name,
                source_type=source_type,
                subject=document.subject,
                educational_level=document.educational_level,
                language=document.language,
                chapter=chapter,
            )
            if not chunks:
                raise DocumentError("تعذّر تقسيم الوثيقة إلى مقاطع.", "chunking_failed")

            vectors = self.embeddings.embed_batch([chunk["text"] for chunk in chunks])
            if len(vectors) != len(chunks):
                raise DocumentError("عدد التمثيلات لا يطابق عدد المقاطع.", "embedding_mismatch")

            for chunk, vector in zip(chunks, vectors):
                page_number = (chunk["metadata"] or {}).get("page_number")
                db.session.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_id=chunk["chunk_id"],
                        chunk_index=chunk["chunk_index"],
                        text=chunk["text"],
                        page_number=page_number if isinstance(page_number, int) else None,
                        subject=document.subject,
                        educational_level=document.educational_level,
                        language=document.language,
                        created_at=_now(),
                    )
                )

            self.chroma.add_chunks(
                [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "embedding": vector,
                        "metadata": sanitize_metadata(chunk["metadata"]),
                    }
                    for chunk, vector in zip(chunks, vectors)
                ]
            )
            document.status = "ready"
            document.chunk_count = len(chunks)
            db.session.commit()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            self._mark_failed(document.id, safe_error_message(exc))
            raise

        return {
            "success": True,
            "duplicate": False,
            "document_id": document.id,
            "title": document.title,
            "number_of_chunks": len(chunks),
            "source_type": source_type,
            "message": "تمت إضافة الوثيقة إلى قاعدة المعرفة.",
        }

    def _mark_failed(self, document_id: int, message: str) -> None:
        try:
            document = db.session.get(Document, document_id)
            if document is None:
                return
            document.status = "failed"
            document.error_message = message[:1000]
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _build_chunks(
        self,
        extracted: Dict[str, Any],
        *,
        document_id: int,
        filename: str,
        source_type: str,
        subject: Optional[str],
        educational_level: Optional[str],
        language: Optional[str],
        chapter: Optional[str],
    ) -> List[Dict[str, Any]]:
        pages = extracted.get("page_texts") or [{"page_number": 1, "text": extracted.get("text", "")}]
        chunks: List[Dict[str, Any]] = []
        for page in pages:
            metadata = {
                "document_id": document_id,
                "filename": filename,
                "source_type": source_type,
                "subject": subject,
                "educational_level": educational_level,
                "language": language,
                "chapter": chapter,
                "page_number": page.get("page_number"),
            }
            chunks.extend(
                self.chunking.chunk(page.get("text") or "", metadata, start_index=len(chunks))
            )
        return chunks

    # -- queries ------------------------------------------------------
    @staticmethod
    def list_documents(
        *,
        subject: Optional[str] = None,
        educational_level: Optional[str] = None,
        source_type: Optional[str] = None,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 24,
    ) -> Dict[str, Any]:
        statement = Document.query
        if subject:
            statement = statement.filter(Document.subject == subject)
        if educational_level:
            statement = statement.filter(Document.educational_level == educational_level)
        if source_type:
            statement = statement.filter(Document.source_type == source_type)
        if query:
            statement = statement.filter(Document.title.ilike(f"%{query.strip()}%"))
        pagination = statement.order_by(Document.created_at.desc()).paginate(
            page=max(1, page), per_page=max(1, min(per_page, 100)), error_out=False
        )
        return {
            "items": [DocumentService.serialize(document) for document in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
        }

    @staticmethod
    def serialize(document: Document) -> Dict[str, Any]:
        suffix = Path(document.file_path).suffix.lower().lstrip(".")
        return {
            "document_id": document.id,
            "title": document.title,
            "filename": f"{document.title}.{suffix}" if suffix else document.title,
            "file_type": suffix.upper() or None,
            "source_type": document.source_type,
            "source_type_label": {
                "official": "وثيقة رسمية",
                "teacher_upload": "وثيقة المعلّم",
                "web": "مرجع ويب",
            }.get(document.source_type, document.source_type),
            "subject": document.subject,
            "educational_level": document.educational_level,
            "language": document.language,
            "chapter": document.chapter,
            "file_size": document.file_size or 0,
            "status": document.status or "ready",
            "error_message": document.error_message,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "number_of_chunks": document.chunk_count or len(document.chunks or []),
        }

    @staticmethod
    def get(document_id: int) -> Optional[Document]:
        return db.session.get(Document, document_id)

    # -- deletion -----------------------------------------------------
    def delete(self, document_id: int) -> bool:
        document = db.session.get(Document, document_id)
        if document is None:
            return False
        file_path = document.file_path
        self.chroma.delete_document(document_id)
        db.session.delete(document)
        db.session.commit()
        try:
            if file_path and os.path.isfile(file_path):
                os.remove(file_path)
        except OSError:
            logger.warning("Could not remove uploaded file %s", file_path)
        return True

    # -- maintenance --------------------------------------------------
    def reindex(self, document_id: int) -> Dict[str, Any]:
        """Rebuild vectors for one document from its stored chunks."""
        document = db.session.get(Document, document_id)
        if document is None:
            raise DocumentError("الوثيقة غير موجودة.", "not_found")
        chunks = list(document.chunks)
        if not chunks:
            raise DocumentError("لا توجد مقاطع لإعادة فهرستها.", "no_chunks")
        vectors = self.embeddings.embed_batch([chunk.text for chunk in chunks])
        self.chroma.delete_document(document.id)
        self.chroma.add_chunks(
            [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "embedding": vector,
                    "metadata": sanitize_metadata(
                        {
                            "document_id": document.id,
                            "filename": document.title,
                            "source_type": document.source_type,
                            "subject": document.subject,
                            "educational_level": document.educational_level,
                            "language": document.language,
                            "chapter": document.chapter,
                            "page_number": chunk.page_number,
                        }
                    ),
                }
                for chunk, vector in zip(chunks, vectors)
            ]
        )
        document.status = "ready"
        document.chunk_count = len(chunks)
        db.session.commit()
        return {"success": True, "number_of_chunks": len(chunks)}

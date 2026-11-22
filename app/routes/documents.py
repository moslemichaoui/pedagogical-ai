"""Knowledge-base pages and document API."""
from __future__ import annotations

import os
import uuid

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    url_for,
)
from app.errors import ApiError
from app.services.document_service import (
    DEFAULT_SOURCE_TYPE,
    DocumentService,
    safe_error_message,
)
from app.services.extraction_service import ExtractionService
from app.services.retrieval_service import RetrievalService
from app.utils.rate_limit import rate_limit
from app.utils.text import parse_int

bp = Blueprint("documents", __name__)


@bp.get("/documents")
def documents_page():
    page = parse_int(request.args.get("page"), 1, 1, 9999)
    result = DocumentService.list_documents(
        subject=request.args.get("subject") or None,
        educational_level=request.args.get("level") or None,
        source_type=request.args.get("source_type") or None,
        query=request.args.get("q") or None,
        page=page,
        per_page=12,
    )
    return render_template(
        "knowledge_base.html",
        page_title="قاعدة المعرفة",
        result=result,
        filters={
            "subject": request.args.get("subject", ""),
            "level": request.args.get("level", ""),
            "source_type": request.args.get("source_type", ""),
            "q": request.args.get("q", ""),
        },
        stats=RetrievalService().stats(),
    )


@bp.get("/documents/<int:document_id>")
def document_detail(document_id: int):
    document = DocumentService.get(document_id)
    if document is None:
        abort(404)
    chunks = sorted(document.chunks, key=lambda chunk: chunk.chunk_index or 0)
    return render_template(
        "document_detail.html",
        page_title=document.title,
        document=document,
        chunks=chunks,
        meta=DocumentService.serialize(document),
    )


@bp.post("/api/documents/upload")
@rate_limit("upload", "RATE_LIMIT_UPLOAD_PER_HOUR")
def upload_document():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        raise ApiError(
            "يرجى اختيار ملف للرفع.",
            status=400,
            code="file_required",
        )

    original = uploaded.filename
    suffix = os.path.splitext(original)[1].lower()
    if suffix not in ExtractionService.SAFE_EXTENSIONS:
        allowed = "، ".join(sorted(ext.lstrip(".").upper() for ext in ExtractionService.SAFE_EXTENSIONS))
        raise ApiError(f"صيغة غير مدعومة. الصيغ المقبولة: {allowed}.", status=415, code="unsupported_type")

    safe_name = ExtractionService.sanitize_filename(original) or f"document{suffix}"
    stem, extension = os.path.splitext(safe_name)
    save_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        f"{stem}_{uuid.uuid4().hex[:8]}{extension or suffix}",
    )
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    uploaded.save(save_path)

    try:
        result = DocumentService().ingest(
            save_path,
            filename=original,
            source_type=request.form.get("source_type") or DEFAULT_SOURCE_TYPE,
            subject=request.form.get("subject") or None,
            educational_level=request.form.get("educational_level") or None,
            language=request.form.get("language") or "ar",
            chapter=request.form.get("chapter") or None,
        )
    except Exception as exc:  # noqa: BLE001
        _remove(save_path)
        code = getattr(exc, "code", "ingestion_failed")
        status = 409 if code == "duplicate" else 400
        raise ApiError(safe_error_message(exc), status=status, code=code) from exc

    if result.get("duplicate"):
        _remove(save_path)

    return (
        jsonify(
            {
                **result,
                "redirect_url": url_for("documents.document_detail", document_id=result["document_id"]),
            }
        ),
        200 if result.get("duplicate") else 201,
    )


@bp.get("/api/documents")
def list_documents():
    result = DocumentService.list_documents(
        subject=request.args.get("subject") or None,
        educational_level=request.args.get("level") or None,
        source_type=request.args.get("source_type") or None,
        query=request.args.get("q") or None,
        page=parse_int(request.args.get("page"), 1, 1, 9999),
        per_page=parse_int(request.args.get("per_page"), 12, 1, 100),
    )
    return jsonify({"success": True, "count": result["total"], **result})


@bp.get("/api/documents/<int:document_id>")
def get_document(document_id: int):
    document = DocumentService.get(document_id)
    if document is None:
        raise ApiError("الوثيقة غير موجودة.", status=404, code="not_found")
    return jsonify({"success": True, "document": DocumentService.serialize(document)})


@bp.delete("/api/documents/<int:document_id>")
def delete_document(document_id: int):
    if not DocumentService().delete(document_id):
        raise ApiError("الوثيقة غير موجودة.", status=404, code="not_found")
    return jsonify({"success": True, "deleted": document_id})


@bp.post("/api/documents/<int:document_id>/reindex")
def reindex_document(document_id: int):
    try:
        result = DocumentService().reindex(document_id)
    except ValueError as exc:
        raise ApiError(
            safe_error_message(exc),
            status=400,
            code=getattr(exc, "code", "reindex_failed"),
        ) from exc
    return jsonify(result)


@bp.get("/api/documents/retrieve")
def retrieve_documents():
    results = RetrievalService().retrieve(
        topic=request.args.get("topic") or request.args.get("q"),
        subject=request.args.get("subject") or None,
        educational_level=request.args.get("educational_level") or None,
        language=request.args.get("language") or None,
        n_results=parse_int(request.args.get("n_results"), 5, 1, 20),
    )
    return jsonify({"success": True, "count": len(results), "results": results})


def _remove(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        current_app.logger.warning("Could not remove upload %s", path)

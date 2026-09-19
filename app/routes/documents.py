from flask import Blueprint, current_app, jsonify, request

from app.models import Document
from app.services.document_service import DEFAULT_SOURCE_TYPE, DocumentService
from app.services.extraction_service import ExtractionService
from app.services.retrieval_service import RetrievalService

bp = Blueprint('documents', __name__)


@bp.route('/api/documents/upload', methods=['POST'])
def upload_document():
    uploaded = request.files.get('file')
    if uploaded is None or not uploaded.filename:
        return jsonify({
            'success': False,
            'document_id': None,
            'filename': None,
            'number_of_chunks': 0,
            'source_type': None,
            'message': 'A file is required (multipart field name: file)',
        }), 400

    original_name = uploaded.filename
    safe_name = ExtractionService.sanitize_filename(original_name) or 'upload.txt'
    save_path = _unique_save_path(current_app.config['UPLOAD_FOLDER'], safe_name)
    uploaded.save(save_path)

    try:
        result = DocumentService().ingest(
            file_path=save_path,
            filename=safe_name,
            source_type=request.form.get('source_type') or DEFAULT_SOURCE_TYPE,
            subject=request.form.get('subject') or None,
            educational_level=request.form.get('educational_level') or None,
            language=request.form.get('language') or 'ar',
            chapter=request.form.get('chapter') or None,
        )
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({
            'success': False,
            'document_id': None,
            'filename': safe_name,
            'number_of_chunks': 0,
            'source_type': request.form.get('source_type') or DEFAULT_SOURCE_TYPE,
            'message': str(exc),
        }), 400
    except Exception as exc:
        return jsonify({
            'success': False,
            'document_id': None,
            'filename': safe_name,
            'number_of_chunks': 0,
            'source_type': request.form.get('source_type') or DEFAULT_SOURCE_TYPE,
            'message': f'Ingestion failed: {exc}',
        }), 500


@bp.route('/api/documents', methods=['GET'])
def list_documents():
    documents = DocumentService().list_documents()
    return jsonify({
        'success': True,
        'count': len(documents),
        'documents': documents,
    })


@bp.route('/api/documents/<int:document_id>', methods=['GET'])
def get_document(document_id):
    document = Document.query.get(document_id)
    if document is None:
        return jsonify({'success': False, 'message': 'Document not found'}), 404
    return jsonify({
        'success': True,
        'document_id': document.id,
        'title': document.title,
        'source_type': document.source_type,
        'subject': document.subject,
        'educational_level': document.educational_level,
        'language': document.language,
        'number_of_chunks': len(document.chunks),
    })


@bp.route('/api/documents/retrieve', methods=['GET'])
def retrieve_documents():
    results = RetrievalService().retrieve(
        topic=request.args.get('topic'),
        subject=request.args.get('subject'),
        educational_level=request.args.get('educational_level'),
        language=request.args.get('language'),
        n_results=int(request.args.get('n_results') or 5),
    )
    return jsonify({
        'success': True,
        'count': len(results),
        'results': results,
    })


def _unique_save_path(upload_folder, filename):
    import os
    import uuid

    os.makedirs(upload_folder, exist_ok=True)
    stem, suffix = os.path.splitext(filename)
    unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    return os.path.join(upload_folder, unique_name)

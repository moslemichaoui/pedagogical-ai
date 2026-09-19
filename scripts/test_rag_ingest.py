"""End-to-end RAG ingestion checks. Run from the project root."""
import os
import sys
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    results = []

    def check(name, ok, detail=''):
        results.append((name, bool(ok), detail))
        status = 'PASS' if ok else 'FAIL'
        print(f'[{status}] {name}' + (f' — {detail}' if detail else ''))

    print('=== RAG ingestion tests ===')

    try:
        from app import create_app, db
        from app.models import Document, DocumentChunk
        from app.ai.embeddings import MockEmbeddingProvider, get_embedding_provider
        from app.services.chroma_db import ChromaService
        from app.services.retrieval_service import RetrievalService
        check('python imports', True)
    except Exception as exc:
        check('python imports', False, str(exc))
        return 1

    mock = MockEmbeddingProvider()
    vector = mock.embed('الإيقاظ العلمي')
    check('mock embedding dimension is 768', len(vector) == 768, f'dim={len(vector)}')

    app = None
    try:
        app = create_app()
        check('Flask create_app()', True)
    except Exception as exc:
        check('Flask create_app()', False, str(exc))
        return 1

    phrase = 'النباتات الخضراء تصنع غذاءها بواسطة عملية البناء الضوئي'
    document_id = None
    saved_upload = None

    with app.app_context():
        table_names = set(db.inspect(db.engine).get_table_names())
        expected = {
            'users', 'documents', 'document_chunks',
            'lessons', 'exercises', 'assessments', 'generation_requests',
        }
        missing = expected - table_names
        check('database tables created', not missing, f'missing={sorted(missing)} tables={sorted(table_names)}')

        provider = get_embedding_provider()
        check(
            'embedding provider available',
            provider.is_available(),
            type(provider).__name__,
        )

        client = app.test_client()
        payload = (
            f'{phrase}. هذا نص تجريبي لمنصة الإيقاظ العلمي في السنة الخامسة ابتدائي. '
            f'يستخدم لاختبار الفهرسة والاسترجاع الدلالي.'
        ).encode('utf-8')

        fd, temp_path = tempfile.mkstemp(suffix='.txt', prefix='rag_test_')
        try:
            os.write(fd, payload)
            os.close(fd)
            with open(temp_path, 'rb') as handle:
                response = client.post(
                    '/api/documents/upload',
                    data={
                        'file': (handle, 'photosynthesis_ar.txt'),
                        'source_type': 'teacher_upload',
                        'subject': 'الإيقاظ العلمي',
                        'educational_level': 'س5',
                        'language': 'ar',
                    },
                    content_type='multipart/form-data',
                )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        check('POST /api/documents/upload', response.status_code in (200, 201), f'status={response.status_code} body={response.get_data(as_text=True)[:500]}')
        body = response.get_json(silent=True) or {}
        check('upload JSON success', body.get('success') is True, str(body))
        check('source_type is teacher_upload', body.get('source_type') == 'teacher_upload', str(body.get('source_type')))
        document_id = body.get('document_id')
        check('chunks created', (body.get('number_of_chunks') or 0) > 0, str(body.get('number_of_chunks')))

        if document_id:
            document = Document.query.get(document_id)
            chunks = DocumentChunk.query.filter_by(document_id=document_id).all()
            check('Document row exists', document is not None)
            check('DocumentChunk rows exist', len(chunks) > 0, f'count={len(chunks)}')
            if document is not None:
                saved_upload = document.file_path
                check('document source_type semantic', document.source_type == 'teacher_upload', document.source_type)

        chroma = ChromaService()
        chroma_count = chroma.count()
        check('ChromaDB has vectors', chroma_count > 0, f'count={chroma_count}')

        retrieved = RetrievalService().retrieve(topic='البناء الضوئي', language='ar', n_results=5)
        check('retrieval returned results', len(retrieved) > 0, f'count={len(retrieved)}')
        joined = ' '.join(item.get('text') or '' for item in retrieved)
        check('retrieval finds uploaded text', 'البناء الضوئي' in joined or phrase[:20] in joined, joined[:300])

        listed = client.get('/api/documents')
        listed_json = listed.get_json(silent=True) or {}
        check('GET /api/documents', listed.status_code == 200 and listed_json.get('success') is True)

        if document_id:
            chroma.delete_document(document_id)
            DocumentChunk.query.filter_by(document_id=document_id).delete()
            Document.query.filter_by(id=document_id).delete()
            db.session.commit()

    if saved_upload and os.path.exists(saved_upload):
        os.remove(saved_upload)
        check('cleaned temporary upload file', True, saved_upload)
    else:
        check('cleaned temporary upload file', saved_upload is None or not os.path.exists(saved_upload), str(saved_upload))

    failed = [name for name, ok, _ in results if not ok]
    print('=== summary ===')
    print(f'{len(results) - len(failed)}/{len(results)} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

"""Focused Phase 4 Knowledge Base checks without live Gemini or ChromaDB."""
import io
import os
import shutil
import sys
import tempfile
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestConfig:
    SECRET_KEY = 'phase4-test'
    SQLALCHEMY_DATABASE_URI = ''
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = ''
    CHROMA_PERSIST_DIR = ''
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024


class FakeEmbeddingService:
    def embed_batch(self, texts):
        return [[0.0] * 768 for _ in texts]

    def get_dimension(self):
        return 768


class FakeChromaService:
    stored_chunks = []

    def add_chunks(self, chunks):
        self.stored_chunks.extend(chunks)
        return True

    def delete_document(self, document_id):
        self.stored_chunks = [
            chunk for chunk in self.stored_chunks
            if chunk['metadata'].get('document_id') != document_id
        ]
        return True


def main():
    results = []

    def check(name, ok, detail=''):
        results.append((name, bool(ok), detail))
        safe_detail = str(detail).encode('ascii', 'backslashreplace').decode('ascii')
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f' — {safe_detail}' if detail else ''))

    workspace = tempfile.mkdtemp(prefix='pedagogical_ai_phase4_')
    TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(workspace, 'phase4.db')}"
    TestConfig.UPLOAD_FOLDER = os.path.join(workspace, 'uploads')
    TestConfig.CHROMA_PERSIST_DIR = os.path.join(workspace, 'chroma')

    try:
        from app import create_app, db
        from app.models import Document, DocumentChunk

        app = create_app(TestConfig)
        client = app.test_client()

        page = client.get('/documents')
        check('GET /documents', page.status_code == 200 and 'قاعدة المعرفة' in page.get_data(as_text=True))
        check('Knowledge Base is RTL', 'dir="rtl"' in page.get_data(as_text=True))
        check('Sidebar link works', 'href="/documents"' in page.get_data(as_text=True))
        check('Upload form fields', all(field in page.get_data(as_text=True) for field in ('name="file"', 'name="source_type"', 'name="subject"', 'name="educational_level"', 'name="language"', 'name="chapter"')))

        empty_list = client.get('/api/documents')
        check('GET /api/documents', empty_list.status_code == 200 and empty_list.get_json()['documents'] == [])

        with patch('app.services.document_service.EmbeddingService', FakeEmbeddingService), \
             patch('app.services.document_service.ChromaService', FakeChromaService):
            upload = client.post(
                '/api/documents/upload',
                data={
                    'file': (io.BytesIO('وثيقة عن دورة الماء في الطبيعة.'.encode('utf-8')), 'water_cycle.txt'),
                    'source_type': 'teacher_upload',
                    'subject': 'الإيقاظ العلمي',
                    'educational_level': 'السنة الثالثة ابتدائي',
                    'language': 'ar',
                    'chapter': 'الوحدة الأولى',
                },
                content_type='multipart/form-data',
            )

        upload_body = upload.get_json() or {}
        document_id = upload_body.get('document_id')
        check('upload TXT', upload.status_code == 201 and upload_body.get('success') is True, str(upload_body))
        check('upload creates chunks', (upload_body.get('number_of_chunks') or 0) > 0)

        with app.app_context():
            document = db.session.get(Document, document_id)
            chunk_count = DocumentChunk.query.filter_by(document_id=document_id).count()
            check('metadata persistence', document.subject == 'الإيقاظ العلمي' and document.language == 'ar')
            check('chapter persistence', document.chapter == 'الوحدة الأولى')
            check('DocumentChunk records created', chunk_count > 0, f'count={chunk_count}')
            columns = {column['name'] for column in db.inspect(db.engine).get_columns('documents')}
            check('documents.chapter database column', 'chapter' in columns)

        listed = client.get('/api/documents')
        listed_body = listed.get_json() or {}
        item = next((doc for doc in listed_body.get('documents', []) if doc['document_id'] == document_id), {})
        check('document list serialization', all(key in item for key in ('filename', 'file_type', 'chapter', 'created_at', 'processing_status')))
        check('list values', item.get('filename') == 'water_cycle.txt' and item.get('chapter') == 'الوحدة الأولى' and item.get('processing_status') == 'processed', str(item))

        detail = client.get(f'/api/documents/{document_id}')
        detail_body = detail.get_json() or {}
        check('document detail API compatibility', detail.status_code == 200 and detail_body.get('chapter') == 'الوحدة الأولى' and detail_body.get('filename') == 'water_cycle.txt')

        with patch('app.routes.documents.RetrievalService.retrieve', return_value=[]):
            retrieval = client.get('/api/documents/retrieve?topic=دورة+الماء')
        check('document retrieval API compatibility', retrieval.status_code == 200 and retrieval.get_json().get('success') is True)

        with patch('app.routes.documents.DocumentService.ingest', side_effect=ValueError('Synthetic ingestion failure')):
            failed_upload = client.post(
                '/api/documents/upload',
                data={'file': (io.BytesIO(b'failure fixture'), 'failed.txt')},
                content_type='multipart/form-data',
            )
        remaining_files = []
        if os.path.isdir(TestConfig.UPLOAD_FOLDER):
            remaining_files = os.listdir(TestConfig.UPLOAD_FOLDER)
        check('failed ingestion returns existing error format', failed_upload.status_code == 400 and failed_upload.get_json().get('message') == 'Synthetic ingestion failure')
        check('failed ingestion cleanup', all('failed' not in name for name in remaining_files), str(remaining_files))
    except Exception as exc:
        check('Phase 4 test execution', False, repr(exc))
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    failed = [name for name, ok, _ in results if not ok]
    print('=== summary ===')
    print(f'{len(results) - len(failed)}/{len(results)} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

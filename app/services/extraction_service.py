"""Service for document extraction with validation and safety checks."""
import os
import re
from pathlib import Path
from typing import Optional


class ExtractionService:
    """Handles safe document text extraction with validation."""

    SAFE_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_TEXT_LENGTH = 10 * 1024 * 1024  # 10 MB of text

    @staticmethod
    def validate_file(file_path: str) -> dict:
        """Validate a file before extraction."""
        if not os.path.exists(file_path):
            return {'valid': False, 'error': 'File not found'}

        if not os.path.isfile(file_path):
            return {'valid': False, 'error': 'Not a file'}

        file_size = os.path.getsize(file_path)
        if file_size > ExtractionService.MAX_FILE_SIZE:
            return {'valid': False, 'error': f'File too large: {file_size} bytes'}

        ext = Path(file_path).suffix.lower()
        if ext not in ExtractionService.SAFE_EXTENSIONS:
            return {'valid': False, 'error': f'Unsupported extension: {ext}'}

        if '..' in Path(file_path).parts:
            return {'valid': False, 'error': 'Path traversal detected'}

        return {'valid': True, 'error': None}

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize a filename to prevent path traversal."""
        basename = os.path.basename(filename)
        sanitized = re.sub(r'[^\w\s\-.]', '', basename, flags=re.UNICODE)
        sanitized = sanitized.replace(' ', '_')
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        return sanitized

    @staticmethod
    def extract_text(file_path: str) -> dict:
        """Extract text from a document file safely.

        Returns:
            dict with 'text', 'pages', 'page_texts', optional metadata, or 'error'
        """
        validation = ExtractionService.validate_file(file_path)
        if not validation['valid']:
            return {'error': validation['error'], 'text': '', 'pages': [], 'page_texts': []}

        ext = Path(file_path).suffix.lower()

        if ext == '.pdf':
            return ExtractionService._extract_pdf(file_path)
        if ext == '.docx':
            return ExtractionService._extract_docx(file_path)
        if ext == '.txt':
            return ExtractionService._extract_txt(file_path)

        return {'error': f'Unsupported file type: {ext}', 'text': '', 'pages': [], 'page_texts': []}

    @staticmethod
    def _limit_text(text: str) -> str:
        if len(text) > ExtractionService.MAX_TEXT_LENGTH:
            return text[:ExtractionService.MAX_TEXT_LENGTH]
        return text

    @staticmethod
    def _extract_pdf(file_path: str) -> dict:
        """Extract text from a PDF file using PyMuPDF (`import fitz`)."""
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            return {
                'error': 'PDF extraction failed: pymupdf is not installed',
                'text': '',
                'pages': [],
                'page_texts': [],
            }

        try:
            doc = fitz.open(file_path)
            page_texts = []

            for i in range(len(doc)):
                page = doc.load_page(i)
                page_text = page.get_text()
                if page_text.strip():
                    page_texts.append({
                        'page_number': i + 1,
                        'text': page_text.strip(),
                    })

            doc.close()

            text = ExtractionService._limit_text(
                "\n\n".join(item['text'] for item in page_texts)
            )
            pages = [item['page_number'] for item in page_texts]

            return {
                'text': text,
                'pages': pages,
                'page_texts': page_texts,
                'subject': None,
                'language': 'ar',
                'level': None,
                'chapter': None,
            }
        except Exception as e:
            return {'error': f'PDF extraction failed: {str(e)}', 'text': '', 'pages': [], 'page_texts': []}

    @staticmethod
    def _extract_docx(file_path: str) -> dict:
        """Extract text from a DOCX file using python-docx."""
        try:
            from docx import Document as DocxDocument
        except ImportError:
            return {
                'error': 'DOCX extraction failed: python-docx is not installed',
                'text': '',
                'pages': [],
                'page_texts': [],
            }

        try:
            doc = DocxDocument(file_path)
            page_map = {}

            for i, paragraph in enumerate(doc.paragraphs):
                if not paragraph.text.strip():
                    continue
                page_num = (i // 25) + 1
                page_map.setdefault(page_num, [])
                page_map[page_num].append(paragraph.text.strip())

            page_texts = [
                {'page_number': page_num, 'text': "\n\n".join(parts)}
                for page_num, parts in sorted(page_map.items())
            ]
            if not page_texts:
                page_texts = [{'page_number': 1, 'text': ''}]

            text = ExtractionService._limit_text(
                "\n\n".join(item['text'] for item in page_texts if item['text'])
            )
            pages = [item['page_number'] for item in page_texts if item['text']] or [1]

            return {
                'text': text,
                'pages': pages,
                'page_texts': page_texts,
                'subject': None,
                'language': 'ar',
                'level': None,
                'chapter': None,
            }
        except Exception as e:
            return {'error': f'DOCX extraction failed: {str(e)}', 'text': '', 'pages': [], 'page_texts': []}

    @staticmethod
    def _extract_txt(file_path: str) -> dict:
        """Extract text from a TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = ExtractionService._limit_text(f.read())

            page_texts = [{'page_number': 1, 'text': text.strip()}] if text.strip() else []

            return {
                'text': text,
                'pages': [1] if text.strip() else [],
                'page_texts': page_texts,
                'subject': None,
                'language': 'ar',
                'level': None,
                'chapter': None,
            }
        except Exception as e:
            return {'error': f'TXT extraction failed: {str(e)}', 'text': '', 'pages': [], 'page_texts': []}

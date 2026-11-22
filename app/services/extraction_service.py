"""Safe document text extraction for PDF, DOCX and TXT files."""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.config_values import config_value
from app.utils.text import clean_text

logger = logging.getLogger(__name__)


class ExtractionService:
    """Validate and extract text from teacher-uploaded documents."""

    SAFE_EXTENSIONS = {".pdf", ".docx", ".txt"}
    MAX_FILE_SIZE = 25 * 1024 * 1024
    MAX_TEXT_LENGTH = 8 * 1024 * 1024

    @staticmethod
    def validate_file(file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"valid": False, "error": "الملف غير موجود."}
        if not path.is_file():
            return {"valid": False, "error": "المسار لا يشير إلى ملف."}
        if path.stat().st_size == 0:
            return {"valid": False, "error": "الملف فارغ."}
        if path.stat().st_size > ExtractionService.MAX_FILE_SIZE:
            limit = ExtractionService.MAX_FILE_SIZE // (1024 * 1024)
            return {"valid": False, "error": f"حجم الملف يتجاوز {limit} ميغابايت."}
        if path.suffix.lower() not in ExtractionService.SAFE_EXTENSIONS:
            allowed = "، ".join(sorted(ext.lstrip(".").upper() for ext in ExtractionService.SAFE_EXTENSIONS))
            return {"valid": False, "error": f"صيغة غير مدعومة. الصيغ المقبولة: {allowed}."}
        return {"valid": True, "error": None}

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        basename = os.path.basename(filename or "")
        sanitized = re.sub(r"[^\w\u0600-\u06FF\s\-.()]", "", basename, flags=re.UNICODE)
        sanitized = re.sub(r"\s+", "_", sanitized).strip("._")
        return sanitized[:180]

    @staticmethod
    def checksum(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def extract_text(file_path: str) -> Dict[str, Any]:
        validation = ExtractionService.validate_file(file_path)
        if not validation["valid"]:
            return {"error": validation["error"], "text": "", "pages": [], "page_texts": []}
        suffix = Path(file_path).suffix.lower()
        if suffix == ".pdf":
            return ExtractionService._extract_pdf(file_path)
        if suffix == ".docx":
            return ExtractionService._extract_docx(file_path)
        return ExtractionService._extract_txt(file_path)

    @staticmethod
    def _limit(text: str) -> str:
        return text[: ExtractionService.MAX_TEXT_LENGTH]

    @staticmethod
    def _extract_pdf(file_path: str) -> Dict[str, Any]:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return {
                "error": "استخراج PDF غير متاح: حزمة pymupdf غير مثبّتة.",
                "text": "",
                "pages": [],
                "page_texts": [],
            }
        try:
            document = fitz.open(file_path)
            page_texts: List[Dict[str, Any]] = []
            for index in range(len(document)):
                text = document.load_page(index).get_text("text")
                if text and text.strip():
                    page_texts.append({"page_number": index + 1, "text": text.strip()})
            document.close()
            if not page_texts:
                return {
                    "error": "الملف لا يحتوي نصاً قابلاً للاستخراج (قد يكون صورة ممسوحة).",
                    "text": "",
                    "pages": [],
                    "page_texts": [],
                }
            return ExtractionService._result(page_texts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF extraction failed: %s", exc)
            return {
                "error": "تعذّر استخراج نص PDF. تأكّد من أن الملف سليم وغير محمي بكلمة مرور.",
                "text": "",
                "pages": [],
                "page_texts": [],
            }

    @staticmethod
    def _extract_docx(file_path: str) -> Dict[str, Any]:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            return {
                "error": "استخراج DOCX غير متاح: حزمة python-docx غير مثبّتة.",
                "text": "",
                "pages": [],
                "page_texts": [],
            }
        try:
            document = DocxDocument(file_path)
            paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        paragraphs.append(" | ".join(cells))
            if not paragraphs:
                return {
                    "error": "الملف لا يحتوي نصاً قابلاً للاستخراج.",
                    "text": "",
                    "pages": [],
                    "page_texts": [],
                }
            page_texts = []
            for start in range(0, len(paragraphs), 25):
                page_texts.append(
                    {
                        "page_number": len(page_texts) + 1,
                        "text": "\n\n".join(paragraphs[start : start + 25]),
                    }
                )
            return ExtractionService._result(page_texts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("DOCX extraction failed: %s", exc)
            return {
                "error": "تعذّر استخراج نص DOCX. تأكّد من أن الملف سليم وغير تالف.",
                "text": "",
                "pages": [],
                "page_texts": [],
            }

    @staticmethod
    def _extract_txt(file_path: str) -> Dict[str, Any]:
        try:
            raw = Path(file_path).read_bytes()
        except OSError as exc:
            logger.warning("Text file read failed: %s", exc)
            return {"error": "تعذّر قراءة الملف النصي.", "text": "", "pages": [], "page_texts": []}
        text = ""
        for encoding in ("utf-8-sig", "utf-8", "cp1256", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if not text.strip():
            return {
                "error": "الملف النصي فارغ.",
                "text": "",
                "pages": [],
                "page_texts": [],
            }
        return ExtractionService._result([{"page_number": 1, "text": text.strip()}])

    @staticmethod
    def _result(page_texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        cleaned_pages = [
            {"page_number": page["page_number"], "text": clean_text(page["text"])}
            for page in page_texts
            if clean_text(page.get("text"))
        ]
        text = ExtractionService._limit("\n\n".join(page["text"] for page in cleaned_pages))
        return {
            "text": text,
            "pages": [page["page_number"] for page in cleaned_pages],
            "page_texts": cleaned_pages,
            "language": "ar",
            "subject": None,
            "level": None,
            "chapter": None,
        }

    @staticmethod
    def guess_metadata(filename: str) -> Dict[str, Optional[str]]:
        """Infer subject/level hints from a filename, without trusting it."""
        stem = Path(filename or "").stem
        subject = next((item for item in config_value("SUBJECTS", []) if item in stem), None)
        level = next((item for item in config_value("LEVELS", []) if item in stem), None)
        return {"subject": subject, "level": level}

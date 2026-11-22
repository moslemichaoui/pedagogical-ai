"""Focused service-layer tests for validation and safe error handling."""
from __future__ import annotations

from app.ai.schemas import LessonPlan
from app.services.document_service import DocumentError, safe_error_message
from app.services.extraction_service import ExtractionService
from app.services.validation_service import ValidationService
from app.utils.text import extract_json, parse_int, scale_durations, split_lines


def test_validation_service_accepts_complete_arabic_plan(sample_plan):
    plan = LessonPlan(**sample_plan)
    result = ValidationService().validate_lesson_plan(plan)
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["score"] >= 70
    assert any(item["key"] == "phases" for item in result["rubric"])


def test_validation_service_rejects_non_arabic_content(sample_plan):
    sample_plan["title"] = "Water cycle"
    sample_plan["competency"] = "Understand the water cycle"
    sample_plan["introduction"] = "Describe evaporation and condensation"
    sample_plan["learning_objectives"] = [
        "Name the stages of the water cycle.",
        "Explain how clouds form.",
    ]
    sample_plan["summary"] = "Water evaporates, condenses, and falls as rain."
    plan = LessonPlan(**sample_plan)
    result = ValidationService().validate_lesson_plan(plan)
    assert result["valid"] is False
    assert any("العربية" in error for error in result["errors"])


def test_generation_request_validation_keeps_arabic_messages():
    result = ValidationService().validate_generation_request({"topic": "م", "duration": 1})
    assert result["valid"] is False
    assert any("المادة" in error for error in result["errors"])
    assert any("المستوى" in error for error in result["errors"])
    assert any("قصير" in error for error in result["errors"])
    assert any("5 و180" in error for error in result["errors"])


def test_safe_error_message_preserves_authored_errors_only():
    assert safe_error_message(DocumentError("الملف مكرر.", code="duplicate")) == "الملف مكرر."
    leaked = RuntimeError("sqlite:///C:/Users/ichao/secret/app.db failed")
    message = safe_error_message(leaked)
    assert "secret" not in message
    assert "sqlite" not in message
    assert "تعذّر معالجة الوثيقة" in message


def test_extraction_validation_rejects_unsupported_file(tmp_path):
    path = tmp_path / "lesson.exe"
    path.write_bytes(b"MZ\x00\x00")
    result = ExtractionService.validate_file(str(path))
    assert result["valid"] is False
    assert "صيغة غير مدعومة" in result["error"]


def test_text_helpers_are_defensive():
    assert parse_int("999", 45, 5, 180) == 180
    assert parse_int("abc", 45, 5, 180) == 45
    assert split_lines("أول\n\n ثانٍ \n") == ["أول", "ثانٍ"]
    assert scale_durations([10, 20], 45) == [15, 30]
    assert extract_json('```json\n{"title":"درس"}\n```') == {"title": "درس"}

"""Lesson generation, retrieval, duplication, deletion and export."""
from __future__ import annotations

import io
import logging

from flask import Blueprint, jsonify, request, send_file, url_for
from pydantic import ValidationError

from app.ai.schemas import GenerationRequest, LessonPlan
from app.errors import ApiError
from app.services.export_service import build_lesson_docx, docx_filename
from app.services.lesson_generation_service import LessonGenerationService
from app.services.lesson_service import LessonService
from app.services.validation_service import ValidationService
from app.utils.rate_limit import rate_limit
from app.utils.text import parse_int, split_lines

logger = logging.getLogger(__name__)

bp = Blueprint("lessons", __name__)


def _payload() -> dict:
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    form = request.form
    return {
        "subject": form.get("subject"),
        "educational_level": form.get("educational_level") or form.get("level"),
        "topic": form.get("topic"),
        "duration": form.get("duration"),
        "objectives": split_lines(form.get("objectives")),
        "difficulty": form.get("difficulty"),
        "language": form.get("language", "ar"),
        "teacher_instructions": form.get("teacher_instructions"),
        "use_documents": form.get("use_documents", "1") not in {"0", "false", "off"},
        "source_document_ids": [
            int(value) for value in form.getlist("source_document_ids") if str(value).isdigit()
        ],
    }


@bp.post("/api/lessons/generate")
@rate_limit("generate", "RATE_LIMIT_GENERATE_PER_HOUR")
def generate_lesson():
    payload = _payload()
    validator = ValidationService()
    check = validator.validate_generation_request(payload)
    if not check["valid"]:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "بيانات الطلب غير مكتملة.",
                    "code": "validation_error",
                    "validation_errors": check["errors"],
                }
            ),
            400,
        )

    payload["duration"] = parse_int(payload.get("duration"), 45, 5, 180)
    try:
        generation_request = GenerationRequest(**payload)
    except ValidationError as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "تعذّر قراءة بيانات الطلب.",
                    "code": "validation_error",
                    "validation_errors": [str(error["msg"]) for error in exc.errors()],
                }
            ),
            400,
        )

    service = LessonGenerationService()
    response = service.generate(generation_request)

    if not response.success:
        status = 503 if response.error_code == "not_configured" else 502
        return (
            jsonify(
                {
                    "success": False,
                    "error": response.error_message,
                    "code": response.error_code or "generation_failed",
                    "validation_errors": response.validation_errors,
                }
            ),
            status,
        )

    return jsonify(
        {
            "success": True,
            "lesson_id": response.lesson_id,
            "lesson_plan": response.lesson_plan.model_dump() if response.lesson_plan else None,
            "validation_errors": response.validation_errors,
            "validation_warnings": response.validation_warnings,
            "retrieved_context_count": response.retrieved_context_count,
            "duration_coherent": response.duration_coherent,
            "model_used": response.model_used,
            "quality": response.quality,
            "redirect_url": url_for("main.lesson_detail", lesson_id=response.lesson_id)
            if response.lesson_id
            else None,
        }
    )


@bp.get("/api/lessons")
def list_lessons():
    result = LessonService.list_lessons(
        subject=request.args.get("subject") or None,
        educational_level=request.args.get("level") or None,
        query=request.args.get("q") or None,
        page=parse_int(request.args.get("page"), 1, 1, 9999),
        per_page=parse_int(request.args.get("per_page"), 12, 1, 48),
    )
    return jsonify({"success": True, **result})


@bp.get("/api/lessons/<int:lesson_id>")
def get_lesson(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        raise ApiError("الجذاذة غير موجودة.", status=404, code="not_found")
    return jsonify({"success": True, "lesson": LessonService.serialize(lesson, include_content=True)})


@bp.delete("/api/lessons/<int:lesson_id>")
def delete_lesson(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        raise ApiError("الجذاذة غير موجودة.", status=404, code="not_found")
    LessonService.delete(lesson)
    return jsonify({"success": True, "deleted": lesson_id})


@bp.post("/api/lessons/<int:lesson_id>/duplicate")
def duplicate_lesson(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        raise ApiError("الجذاذة غير موجودة.", status=404, code="not_found")
    clone = LessonService.duplicate(lesson)
    return (
        jsonify(
            {
                "success": True,
                "lesson_id": clone.id,
                "redirect_url": url_for("main.lesson_detail", lesson_id=clone.id),
            }
        ),
        201,
    )


@bp.get("/api/lessons/<int:lesson_id>/export.docx")
def export_lesson(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        raise ApiError("الجذاذة غير موجودة.", status=404, code="not_found")
    plan = LessonService.plan_of(lesson)
    if plan is None:
        raise ApiError("محتوى الجذاذة غير صالح للتصدير.", status=422, code="invalid_content")
    try:
        content = build_lesson_docx(plan)
    except ImportError:
        raise ApiError(
            "تصدير Word غير متاح: حزمة python-docx غير مثبّتة.",
            status=503,
            code="export_unavailable",
        )
    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=docx_filename(plan),
        max_age=0,
    )


@bp.post("/api/lessons/validate")
def validate_lesson():
    payload = request.get_json(silent=True) or {}
    try:
        plan = LessonPlan(**payload)
    except ValidationError as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "بنية الجذاذة غير صالحة.",
                    "code": "validation_error",
                    "validation_errors": [str(error["msg"]) for error in exc.errors()],
                }
            ),
            400,
        )
    result = ValidationService().validate_lesson_plan(plan)
    return jsonify(
        {
            "success": result["valid"],
            "validation_errors": result["errors"],
            "validation_warnings": result["warnings"],
            "warnings": result["warnings"],
            "score": result["score"],
            "rubric": result["rubric"],
            "error_count": result["error_count"],
            "warning_count": result["warning_count"],
        }
    )


@bp.get("/api/lessons/health")
def lesson_generation_health():
    health = LessonGenerationService().health_check()
    return jsonify(health), 200 if health["status"] == "healthy" else 503

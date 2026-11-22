"""Assessment generation API."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.ai.assessment_schemas import AssessmentGenerationRequest
from app.errors import ApiError
from app.services.assessment_generation_service import AssessmentGenerationService
from app.services.lesson_service import LessonService
from app.utils.rate_limit import rate_limit

bp = Blueprint("assessments", __name__)


@bp.post("/api/lessons/<int:lesson_id>/assessments")
@rate_limit("generate", "RATE_LIMIT_GENERATE_PER_HOUR")
def generate_for_lesson(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        raise ApiError("الجذاذة غير موجودة.", status=404, code="not_found")
    plan = LessonService.plan_of(lesson)
    if plan is None:
        raise ApiError("محتوى الجذاذة غير صالح.", status=422, code="invalid_content")

    payload = request.get_json(silent=True) or {}
    payload["lesson_plan"] = plan.model_dump()
    try:
        generation_request = AssessmentGenerationRequest(**payload)
    except ValidationError as exc:
        raise ApiError(
            "بيانات توليد التقويم غير صالحة.",
            status=400,
            code="validation_error",
            details=[str(error["msg"]) for error in exc.errors()],
        ) from exc

    response = AssessmentGenerationService().generate(generation_request)
    if not response.success:
        return (
            jsonify(
                {
                    "success": False,
                    "error": response.error_message,
                    "code": response.error_code,
                    "validation_errors": response.validation_errors,
                }
            ),
            502,
        )

    saved = AssessmentGenerationService.save_to_lesson(lesson, response.assessments)
    return jsonify(
        {
            "success": True,
            "assessments": [item.model_dump() for item in response.assessments],
            "saved_items": saved,
            "model_used": response.model_used,
        }
    )


@bp.get("/api/lessons/<int:lesson_id>/assessments")
def list_for_lesson(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        raise ApiError("الجذاذة غير موجودة.", status=404, code="not_found")
    items = [item for item in lesson.exercises if item.kind == "assessment"]
    return jsonify(
        {
            "success": True,
            "count": len(items),
            "assessments": [
                {
                    "id": item.id,
                    "type": item.type,
                    "question": item.question,
                    "answer": item.answer,
                    "explanation": item.explanation,
                    "objective": item.objective,
                    "difficulty": item.difficulty,
                    "block": (item.payload or {}).get("block"),
                    "label": (item.payload or {}).get("label"),
                }
                for item in items
            ],
        }
    )


@bp.post("/api/assessments/generate")
@rate_limit("generate", "RATE_LIMIT_GENERATE_PER_HOUR")
def generate_assessments():
    payload = request.get_json(silent=True) or {}
    try:
        generation_request = AssessmentGenerationRequest(**payload)
    except ValidationError as exc:
        raise ApiError(
            "بيانات توليد التقويم غير صالحة.",
            status=400,
            code="validation_error",
            details=[str(error["msg"]) for error in exc.errors()],
        ) from exc
    response = AssessmentGenerationService().generate(generation_request)
    if not response.success:
        return (
            jsonify(
                {
                    "success": False,
                    "error": response.error_message,
                    "code": response.error_code,
                    "validation_errors": response.validation_errors,
                }
            ),
            502,
        )
    return jsonify(
        {
            "success": True,
            "assessments": [item.model_dump() for item in response.assessments],
            "model_used": response.model_used,
        }
    )

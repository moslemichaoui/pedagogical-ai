"""Exercise generation API."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app import db
from app.ai.exercise_schemas import ExerciseGenerationRequest
from app.errors import ApiError
from app.models import Exercise
from app.services.exercise_generation_service import ExerciseGenerationService
from app.services.lesson_service import LessonService
from app.utils.rate_limit import rate_limit
from app.utils.text import parse_int

bp = Blueprint("exercises", __name__)


@bp.post("/api/lessons/<int:lesson_id>/exercises")
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
    payload.setdefault("count", parse_int(request.form.get("count"), 8, 1, 20))
    try:
        generation_request = ExerciseGenerationRequest(**payload)
    except ValidationError as exc:
        raise ApiError(
            "بيانات توليد التمارين غير صالحة.",
            status=400,
            code="validation_error",
            details=[str(error["msg"]) for error in exc.errors()],
        ) from exc

    response = ExerciseGenerationService().generate(generation_request)
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

    exercise_set = response.exercise_set
    Exercise.query.filter_by(lesson_id=lesson.id, kind="exercise").delete()
    for index, item in enumerate(exercise_set.exercises, 1):
        db.session.add(
            Exercise(
                lesson_id=lesson.id,
                kind="exercise",
                type=item.type,
                question=item.question,
                instructions=item.instructions,
                options=item.options,
                answer=item.answer,
                explanation=item.explanation,
                objective=item.objective,
                difficulty=item.difficulty,
                estimated_time=item.estimated_time,
                order_index=index,
                lesson_reference=item.lesson_reference or lesson.title,
            )
        )
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "exercise_set": exercise_set.model_dump(),
            "model_used": response.model_used,
            "count": len(exercise_set.exercises),
        }
    )


@bp.get("/api/lessons/<int:lesson_id>/exercises")
def list_for_lesson(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        raise ApiError("الجذاذة غير موجودة.", status=404, code="not_found")
    items = [item for item in lesson.exercises if item.kind == "exercise"]
    return jsonify(
        {
            "success": True,
            "count": len(items),
            "exercises": [_serialize(item) for item in items],
        }
    )


@bp.delete("/api/exercises/<int:exercise_id>")
def delete_exercise(exercise_id: int):
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        raise ApiError("التمرين غير موجود.", status=404, code="not_found")
    db.session.delete(exercise)
    db.session.commit()
    return jsonify({"success": True, "deleted": exercise_id})


@bp.post("/api/exercises/generate")
@rate_limit("generate", "RATE_LIMIT_GENERATE_PER_HOUR")
def generate_exercises():
    payload = request.get_json(silent=True) or {}
    try:
        generation_request = ExerciseGenerationRequest(**payload)
    except ValidationError as exc:
        raise ApiError(
            "بيانات توليد التمارين غير صالحة.",
            status=400,
            code="validation_error",
            details=[str(error["msg"]) for error in exc.errors()],
        ) from exc
    response = ExerciseGenerationService().generate(generation_request)
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
            "exercise_set": response.exercise_set.model_dump(),
            "validation_errors": [],
            "model_used": response.model_used,
        }
    )


def _serialize(exercise: Exercise) -> dict:
    return {
        "id": exercise.id,
        "type": exercise.type,
        "question": exercise.question,
        "instructions": exercise.instructions,
        "options": exercise.options or [],
        "answer": exercise.answer,
        "explanation": exercise.explanation,
        "objective": exercise.objective,
        "difficulty": exercise.difficulty,
        "estimated_time": exercise.estimated_time,
        "lesson_reference": exercise.lesson_reference,
    }

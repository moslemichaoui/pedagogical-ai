"""Generate exercises from a saved lesson sheet."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.ai.exercise_prompts import EXERCISE_SYSTEM_PROMPT, build_exercise_generation_prompt
from app.ai.exercise_schemas import (
    ExerciseGenerationRequest,
    ExerciseGenerationResponse,
    ExerciseSet,
)
from app.ai.gemini_provider import GeminiError, GeminiErrorType, GeminiProvider
from app.ai.schemas import LessonPlan
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


class ExerciseGenerationService:
    def __init__(self, provider: Optional[GeminiProvider] = None):
        self.provider = provider or GeminiProvider()

    def generate(self, request: ExerciseGenerationRequest) -> ExerciseGenerationResponse:
        if not self.provider.is_available():
            return ExerciseGenerationResponse(
                success=False,
                error_code=GeminiErrorType.NOT_CONFIGURED.value,
                error_message="لم يتم إعداد مفتاح Gemini بعد. أضف GEMINI_API_KEY في ملف .env.",
            )
        try:
            plan = LessonPlan(**request.lesson_plan)
        except Exception as exc:  # noqa: BLE001
            return ExerciseGenerationResponse(
                success=False,
                error_code="invalid_lesson",
                error_message="الجذاذة المحفوظة غير صالحة لتوليد التمارين.",
                validation_errors=[str(exc)[:300]],
            )

        prompt = build_exercise_generation_prompt(
            lesson_plan=plan.model_dump(),
            exercise_types=request.exercise_types,
            count=request.count,
            difficulty=request.difficulty,
            language=request.language,
        )
        try:
            result = self.provider.generate(
                prompt, system_instruction=EXERCISE_SYSTEM_PROMPT, json_mode=True
            )
        except GeminiError as exc:
            return ExerciseGenerationResponse(
                success=False, error_code=exc.code, error_message=exc.message
            )

        payload = extract_json(result.text)
        if payload is None:
            return ExerciseGenerationResponse(
                success=False,
                error_code=GeminiErrorType.INVALID_JSON.value,
                error_message="أعاد النموذج محتوى غير صالح. أعد المحاولة.",
            )

        payload.setdefault("lesson_title", plan.title)
        payload.setdefault("subject", plan.subject)
        payload.setdefault("educational_level", plan.educational_level)
        try:
            exercise_set = ExerciseSet(**payload)
        except Exception as exc:  # noqa: BLE001
            return ExerciseGenerationResponse(
                success=False,
                error_code="invalid_exercises",
                error_message="تعذّر التحقق من التمارين المولّدة.",
                validation_errors=[str(exc)[:300]],
            )

        exercise_set.exercises = exercise_set.exercises[: request.count]
        exercise_set.total_exercises = len(exercise_set.exercises)
        if not exercise_set.exercises:
            return ExerciseGenerationResponse(
                success=False,
                error_code="empty_exercises",
                error_message="لم يُنتج النموذج أي تمرين. أعد المحاولة.",
            )

        return ExerciseGenerationResponse(
            success=True,
            exercise_set=exercise_set,
            model_used=result.model_used,
        )

    @staticmethod
    def serialize(exercise_set: ExerciseSet) -> Dict[str, Any]:
        return exercise_set.model_dump()

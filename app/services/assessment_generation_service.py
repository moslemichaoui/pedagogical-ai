"""Generate formative and summative assessments from a lesson sheet."""
from __future__ import annotations

import logging
from typing import Optional

from app import db
from app.ai.assessment_prompts import (
    ASSESSMENT_SYSTEM_PROMPT,
    build_assessment_generation_prompt,
)
from app.ai.assessment_schemas import (
    AssessmentGenerationRequest,
    AssessmentGenerationResponse,
    AssessmentSet,
)
from app.ai.gemini_provider import GeminiError, GeminiErrorType, GeminiProvider
from app.ai.schemas import LessonPlan
from app.models import Exercise, Lesson
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


class AssessmentGenerationService:
    def __init__(self, provider: Optional[GeminiProvider] = None):
        self.provider = provider or GeminiProvider()

    def generate(self, request: AssessmentGenerationRequest) -> AssessmentGenerationResponse:
        if not self.provider.is_available():
            return AssessmentGenerationResponse(
                success=False,
                error_code=GeminiErrorType.NOT_CONFIGURED.value,
                error_message="لم يتم إعداد مفتاح Gemini بعد. أضف GEMINI_API_KEY في ملف .env.",
            )
        try:
            plan = LessonPlan(**request.lesson_plan)
        except Exception as exc:  # noqa: BLE001
            return AssessmentGenerationResponse(
                success=False,
                error_code="invalid_lesson",
                error_message="الجذاذة المحفوظة غير صالحة لتوليد التقويم.",
                validation_errors=[str(exc)[:300]],
            )

        prompt = build_assessment_generation_prompt(
            lesson_plan=plan.model_dump(),
            kinds=request.kinds,
            count=request.count,
            difficulty=request.difficulty,
            language=request.language,
        )
        try:
            result = self.provider.generate(
                prompt, system_instruction=ASSESSMENT_SYSTEM_PROMPT, json_mode=True
            )
        except GeminiError as exc:
            return AssessmentGenerationResponse(
                success=False, error_code=exc.code, error_message=exc.message
            )

        payload = extract_json(result.text)
        if payload is None:
            return AssessmentGenerationResponse(
                success=False,
                error_code=GeminiErrorType.INVALID_JSON.value,
                error_message="أعاد النموذج محتوى غير صالح. أعد المحاولة.",
            )

        raw_items = payload.get("assessments") or payload.get("items") or []
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        sets = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            raw.setdefault("lesson_title", plan.title)
            raw.setdefault("subject", plan.subject)
            raw.setdefault("educational_level", plan.educational_level)
            try:
                sets.append(AssessmentSet(**raw))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid assessment block: %s", exc)

        if not sets:
            return AssessmentGenerationResponse(
                success=False,
                error_code="empty_assessment",
                error_message="لم يُنتج النموذج أي سؤال تقويم. أعد المحاولة.",
            )

        return AssessmentGenerationResponse(
            success=True,
            assessments=sets,
            model_used=result.model_used,
        )

    @staticmethod
    def save_to_lesson(lesson: Lesson, assessments: list[AssessmentSet]) -> int:
        """Replace the lesson's stored assessment items with the new ones."""
        Exercise.query.filter_by(lesson_id=lesson.id, kind="assessment").delete()
        index = 0
        for assessment in assessments:
            for item in assessment.items:
                index += 1
                db.session.add(
                    Exercise(
                        lesson_id=lesson.id,
                        kind="assessment",
                        type=item.type,
                        question=item.question,
                        answer=item.answer,
                        explanation=item.explanation,
                        objective=item.objective,
                        difficulty=item.difficulty,
                        order_index=index,
                        payload={
                            "block": assessment.kind,
                            "label": assessment.description,
                            "points": item.points,
                        },
                    )
                )
        db.session.commit()
        return index

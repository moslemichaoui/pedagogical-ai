"""Service for generating validated exercises from a lesson plan."""
import json
import logging
from typing import Any, Dict, Optional, List

from app.ai.exercise_schemas import (
    ExerciseGenerationRequest,
    ExerciseGenerationResponse,
    ExerciseSet,
)
from app.ai.exercise_prompts import EXERCISE_SYSTEM_PROMPT, build_exercise_generation_prompt
from app.ai.schemas import LessonPlan
from app.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class ExerciseGenerationService:
    """Generate exercises from an existing validated lesson plan."""

    def __init__(self, gemini_provider: Optional[GeminiProvider] = None):
        self.gemini_provider = gemini_provider or GeminiProvider()

    def generate_exercises(
        self, request: ExerciseGenerationRequest
    ) -> ExerciseGenerationResponse:
        try:
            try:
                validated_lesson = LessonPlan(**request.lesson_plan)
            except Exception as exc:
                return ExerciseGenerationResponse(
                    success=False,
                    validation_errors=[str(exc)],
                    error_message="Invalid lesson plan",
                )

            lesson_plan_data = validated_lesson.model_dump()

            prompt = build_exercise_generation_prompt(
                lesson_plan=lesson_plan_data,
                exercise_types=request.exercise_types,
                count=request.count,
                difficulty=request.difficulty,
                language=request.language,
            )

            try:
                response_text = self.gemini_provider.generate(
                    prompt=f"{EXERCISE_SYSTEM_PROMPT}\n\n{prompt}"
                )
            except RuntimeError as exc:
                logger.warning("Exercise Gemini provider unavailable: %s", exc)
                return ExerciseGenerationResponse(
                    success=False,
                    error_message=f"Gemini API not available: {exc}",
                )

            payload = self._parse_json_response(response_text)
            if payload is None:
                return ExerciseGenerationResponse(
                    success=False,
                    error_message="Failed to parse valid JSON from Gemini response",
                )

            try:
                exercise_set = ExerciseSet(**payload)
            except Exception as exc:
                return ExerciseGenerationResponse(
                    success=False,
                    validation_errors=[str(exc)],
                    error_message="Exercise validation failed",
                )

            if exercise_set.total_exercises != request.count:
                return ExerciseGenerationResponse(
                    success=False,
                    validation_errors=[
                        f"Expected {request.count} exercises, received "
                        f"{exercise_set.total_exercises}"
                    ],
                    error_message="Exercise count validation failed",
                )

            allowed = set(request.exercise_types)
            unexpected = [
                exercise.type
                for exercise in exercise_set.exercises
                if exercise.type not in allowed
            ]
            if unexpected:
                return ExerciseGenerationResponse(
                    success=False,
                    validation_errors=[
                        f"Generated exercise types are not allowed: "
                        f"{', '.join(sorted(set(unexpected)))}"
                    ],
                    error_message="Exercise type validation failed",
                )

            return ExerciseGenerationResponse(
                success=True,
                exercise_set=exercise_set,
            )

        except Exception as exc:
            logger.error("Exercise generation failed: %s", exc, exc_info=True)
            return ExerciseGenerationResponse(
                success=False,
                error_message=f"Exercise generation failed: {exc}",
            )

    @staticmethod
    def _parse_json_response(response_text: str) -> Optional[Dict[str, Any]]:
        if not response_text:
            return None
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        if "```" in response_text:
            lines = response_text.splitlines()
            collected: List[str] = []
            inside = False
            for line in lines:
                if line.strip().startswith("```"):
                    inside = not inside
                    continue
                if inside:
                    collected.append(line)
            try:
                return json.loads("\n".join(collected))
            except json.JSONDecodeError:
                pass

        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response_text[start:end])
            except json.JSONDecodeError:
                return None
        return None

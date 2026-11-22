"""Lesson generation pipeline: retrieve → prompt → generate → validate → save."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app import db
from app.ai.gemini_provider import GeminiError, GeminiErrorType, GeminiProvider
from app.ai.prompts import (
    SYSTEM_PROMPT,
    build_lesson_generation_prompt,
    build_repair_prompt,
)
from app.ai.schemas import (
    GenerationRequest,
    GenerationResponse,
    LessonPlan,
)
from app.models import GenerationRun
from app.services.lesson_service import LessonService
from app.services.retrieval_service import RetrievalService
from app.services.validation_service import ValidationService
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


class LessonGenerationService:
    """Orchestrate one lesson-generation run, including persistence."""

    def __init__(
        self,
        provider: Optional[GeminiProvider] = None,
        retrieval: Optional[RetrievalService] = None,
        validator: Optional[ValidationService] = None,
    ):
        self.provider = provider or GeminiProvider()
        self.retrieval = retrieval or RetrievalService()
        self.validator = validator or ValidationService()

    # -- main entry point ---------------------------------------------
    def generate(self, request: GenerationRequest, *, persist: bool = True) -> GenerationResponse:
        started = time.perf_counter()
        run = GenerationRun(
            kind="lesson",
            request=request.model_dump(),
            status="running",
        )
        db.session.add(run)
        db.session.commit()

        if not self.provider.is_available():
            return self._fail(
                run,
                started,
                "لم يتم إعداد مفتاح Gemini بعد. أضف GEMINI_API_KEY في ملف .env ثم أعد تشغيل التطبيق.",
                code=GeminiErrorType.NOT_CONFIGURED.value,
            )

        context = self._retrieve(request)
        run.retrieved_context_count = len(context)

        prompt = build_lesson_generation_prompt(
            subject=request.subject,
            educational_level=request.educational_level,
            topic=request.topic,
            duration=request.duration,
            objectives=request.objectives,
            difficulty=request.difficulty,
            language=request.language,
            retrieved_context=context,
            teacher_instructions=request.teacher_instructions,
        )

        try:
            plan, model_used = self._generate_plan(prompt)
        except GeminiError as exc:
            logger.warning("Lesson generation failed: %s", exc.detail or exc.code)
            return self._fail(run, started, exc.message, code=exc.code, context_count=len(context))

        plan.normalize_durations()
        validation = self.validator.validate_lesson_plan(plan)
        coherent = plan.validate_duration_coherence(tolerance=0.02)

        lesson_id = None
        if persist:
            lesson = LessonService.create_from_plan(
                plan,
                request_payload=request.model_dump(),
                model_used=model_used,
                retrieved_context_count=len(context),
                duration_coherent=coherent,
                validation_errors=validation["errors"],
                validation_warnings=validation["warnings"],
                source_document_ids=request.source_document_ids,
                status="ready" if validation["valid"] else "review",
            )
            lesson_id = lesson.id

        run.status = "ok"
        run.model_used = model_used
        run.lesson_id = lesson_id
        run.latency_ms = int((time.perf_counter() - started) * 1000)
        db.session.commit()

        return GenerationResponse(
            success=True,
            lesson_plan=plan,
            validation_errors=validation["errors"],
            validation_warnings=validation["warnings"],
            retrieved_context_count=len(context),
            duration_coherent=coherent,
            model_used=model_used,
            lesson_id=lesson_id,
            quality={
                "score": validation["score"],
                "rubric": validation["rubric"],
                "summary": self.validator.rubric_summary(validation),
            },
        )

    # -- steps --------------------------------------------------------
    def _retrieve(self, request: GenerationRequest) -> List[Dict[str, Any]]:
        if not request.use_documents:
            return []
        try:
            return self.retrieval.retrieve(
                subject=request.subject,
                educational_level=request.educational_level,
                topic=request.topic,
                language=request.language,
                n_results=6,
                document_ids=request.source_document_ids or None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Retrieval failed, continuing without sources: %s", exc)
            return []

    def _generate_plan(self, prompt: str) -> tuple[LessonPlan, str]:
        result = self.provider.generate(prompt, system_instruction=SYSTEM_PROMPT, json_mode=True)
        payload = extract_json(result.text)

        if payload is None:
            payload = self._repair(result.text, "المخرجات ليست JSON صالحاً.")

        plan = self._coerce_plan(payload, raw=result.text)
        return plan, result.model_used

    def _repair(self, raw: str, error: str) -> Dict[str, Any]:
        logger.info("Attempting one JSON repair pass")
        try:
            repaired = self.provider.generate(
                build_repair_prompt(raw, error),
                system_instruction=SYSTEM_PROMPT,
                json_mode=True,
            )
        except GeminiError:
            raise
        payload = extract_json(repaired.text)
        if payload is None:
            raise GeminiError(GeminiErrorType.INVALID_JSON, "repair produced invalid JSON")
        return payload

    def _coerce_plan(self, payload: Dict[str, Any], *, raw: str) -> LessonPlan:
        try:
            return LessonPlan(**payload)
        except Exception as exc:  # noqa: BLE001
            logger.info("Lesson payload failed validation, repairing: %s", exc)
            repaired = self._repair(raw, f"فشل التحقق من البنية: {exc}")
            try:
                return LessonPlan(**repaired)
            except Exception as second:  # noqa: BLE001
                raise GeminiError(
                    GeminiErrorType.INVALID_JSON,
                    f"lesson schema mismatch: {second}",
                ) from second

    # -- failure ------------------------------------------------------
    def _fail(
        self,
        run: GenerationRun,
        started: float,
        message: str,
        *,
        code: str,
        context_count: int = 0,
    ) -> GenerationResponse:
        run.status = "error"
        run.error_code = code
        run.latency_ms = int((time.perf_counter() - started) * 1000)
        run.retrieved_context_count = context_count
        db.session.commit()
        return GenerationResponse(
            success=False,
            error_message=message,
            error_code=code,
            retrieved_context_count=context_count,
        )

    # -- health -------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        provider = self.provider.health_check()
        stats = self.retrieval.stats()
        status = "healthy"
        if provider["status"] != "configured":
            status = "degraded"
        if not stats["embeddings_available"]:
            status = "degraded"
        return {
            "service": "lesson_generation",
            "status": status,
            "components": {
                "gemini": provider,
                "retrieval": stats,
            },
        }

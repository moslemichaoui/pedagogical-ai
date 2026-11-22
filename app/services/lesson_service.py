"""Persistence and presentation helpers for saved lesson sheets."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from app import db
from app.ai.schemas import LessonPlan
from app.models import Exercise, Lesson, utcnow

logger = logging.getLogger(__name__)


class LessonService:
    """Create, query, duplicate and delete lesson sheets."""

    # -- writes -------------------------------------------------------
    @staticmethod
    def create_from_plan(
        plan: LessonPlan,
        *,
        request_payload: Optional[Dict[str, Any]] = None,
        model_used: Optional[str] = None,
        retrieved_context_count: int = 0,
        duration_coherent: bool = True,
        validation_errors: Optional[List[str]] = None,
        validation_warnings: Optional[List[str]] = None,
        source_document_ids: Optional[List[int]] = None,
        status: str = "ready",
    ) -> Lesson:
        payload = request_payload or {}
        lesson = Lesson(
            title=plan.title[:300],
            topic=(payload.get("topic") or plan.title)[:300],
            material=plan.subject,
            level=plan.educational_level,
            duration=plan.duration,
            objectives=plan.learning_objectives,
            difficulty=payload.get("difficulty") or "متوسط",
            language=payload.get("language") or "ar",
            reference_documents=", ".join(plan.sources) if plan.sources else None,
            content=plan.model_dump(),
            status=status,
            model_used=model_used,
            retrieved_context_count=retrieved_context_count,
            duration_coherent=duration_coherent,
            validation_errors=validation_errors or [],
            validation_warnings=validation_warnings or [],
            source_document_ids=source_document_ids or [],
        )
        db.session.add(lesson)
        db.session.commit()
        LessonService.sync_assessment_exercises(lesson, plan)
        return lesson

    @staticmethod
    def sync_assessment_exercises(lesson: Lesson, plan: LessonPlan) -> None:
        """Mirror the assessment blocks into ``Exercise`` rows."""
        Exercise.query.filter_by(lesson_id=lesson.id, kind="assessment").delete()
        index = 0
        for block_name, block in (
            ("تكويني", plan.formative_assessment),
            ("نهائي", plan.summative_assessment),
        ):
            for item in block.items:
                index += 1
                db.session.add(
                    Exercise(
                        lesson_id=lesson.id,
                        kind="assessment",
                        type=item.type or "سؤال قصير",
                        question=item.question,
                        answer=item.answer,
                        explanation=item.explanation,
                        objective=item.objective,
                        difficulty=item.difficulty,
                        order_index=index,
                        payload={"block": block_name},
                    )
                )
        db.session.commit()

    @staticmethod
    def update_content(lesson: Lesson, plan: LessonPlan) -> Lesson:
        lesson.content = plan.model_dump()
        lesson.title = plan.title[:300]
        lesson.material = plan.subject
        lesson.level = plan.educational_level
        lesson.duration = plan.duration
        lesson.objectives = plan.learning_objectives
        lesson.updated_at = utcnow()
        db.session.commit()
        LessonService.sync_assessment_exercises(lesson, plan)
        return lesson

    @staticmethod
    def duplicate(lesson: Lesson) -> Lesson:
        clone = Lesson(
            title=f"{lesson.title} (نسخة)"[:300],
            topic=lesson.topic,
            material=lesson.material,
            level=lesson.level,
            duration=lesson.duration,
            objectives=lesson.objectives,
            difficulty=lesson.difficulty,
            language=lesson.language,
            reference_documents=lesson.reference_documents,
            content=lesson.content,
            status="ready",
            model_used=lesson.model_used,
            retrieved_context_count=lesson.retrieved_context_count,
            duration_coherent=lesson.duration_coherent,
            validation_errors=lesson.validation_errors,
            validation_warnings=lesson.validation_warnings,
            source_document_ids=lesson.source_document_ids,
        )
        db.session.add(clone)
        db.session.commit()
        for exercise in lesson.exercises:
            db.session.add(
                Exercise(
                    lesson_id=clone.id,
                    kind=exercise.kind,
                    type=exercise.type,
                    question=exercise.question,
                    instructions=exercise.instructions,
                    options=exercise.options,
                    answer=exercise.answer,
                    explanation=exercise.explanation,
                    objective=exercise.objective,
                    difficulty=exercise.difficulty,
                    estimated_time=exercise.estimated_time,
                    order_index=exercise.order_index,
                    lesson_reference=exercise.lesson_reference,
                    payload=exercise.payload,
                )
            )
        db.session.commit()
        return clone

    @staticmethod
    def delete(lesson: Lesson) -> None:
        db.session.delete(lesson)
        db.session.commit()

    # -- reads --------------------------------------------------------
    @staticmethod
    def get(lesson_id: int) -> Optional[Lesson]:
        return db.session.get(Lesson, lesson_id)

    @staticmethod
    def list_lessons(
        *,
        subject: Optional[str] = None,
        educational_level: Optional[str] = None,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 12,
    ) -> Dict[str, Any]:
        statement = Lesson.query
        if subject:
            statement = statement.filter(Lesson.material == subject)
        if educational_level:
            statement = statement.filter(Lesson.level == educational_level)
        if query:
            like = f"%{query.strip()}%"
            statement = statement.filter(or_(Lesson.title.ilike(like), Lesson.topic.ilike(like)))
        pagination = statement.order_by(Lesson.created_at.desc()).paginate(
            page=max(1, page), per_page=max(1, min(per_page, 48)), error_out=False
        )
        return {
            "items": [LessonService.serialize(item) for item in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
        }

    @staticmethod
    def serialize(lesson: Lesson, *, include_content: bool = False) -> Dict[str, Any]:
        data = {
            "id": lesson.id,
            "lesson_id": lesson.id,
            "title": lesson.title,
            "topic": lesson.topic,
            "subject": lesson.material,
            "educational_level": lesson.level,
            "duration": lesson.duration,
            "difficulty": lesson.difficulty,
            "status": lesson.status,
            "model_used": lesson.model_used,
            "retrieved_context_count": lesson.retrieved_context_count or 0,
            "duration_coherent": bool(lesson.duration_coherent),
            "validation_errors": lesson.validation_errors or [],
            "validation_warnings": lesson.validation_warnings or [],
            "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
            "updated_at": lesson.updated_at.isoformat() if lesson.updated_at else None,
            "exercise_count": sum(1 for item in lesson.exercises if item.kind == "exercise"),
            "assessment_count": sum(1 for item in lesson.exercises if item.kind == "assessment"),
        }
        if include_content:
            data["content"] = lesson.content
        return data

    @staticmethod
    def plan_of(lesson: Lesson) -> Optional[LessonPlan]:
        if not lesson.content:
            return None
        try:
            return LessonPlan(**lesson.content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stored lesson %s no longer validates: %s", lesson.id, exc)
            return None
